from __future__ import annotations

import ctypes

from PySide6.QtCore import QObject, Qt, Signal

from application.command_dispatcher import CommandDispatcher
from application.commands import CommandId
from config.settings import DrawingShortcutSettings, Settings
from core.event_bus import Event, EventBus, Subscription
from core.hotkeys import MOD_ALT, MOD_CONTROL, MOD_SHIFT, parse_hotkey
from core.service import Service
from utils.winapi import (
    HC_ACTION,
    KBDLLHOOKSTRUCT,
    LowLevelKeyboardProc,
    VK_CONTROL,
    VK_ESCAPE,
    VK_LBUTTON,
    VK_LWIN,
    VK_MENU,
    VK_RWIN,
    VK_SHIFT,
    WH_KEYBOARD_LL,
    WM_KEYDOWN,
    WM_SYSKEYDOWN,
    key_down,
    mouse_button_down,
    user32,
)

TOOL_SHORTCUTS = {
    "tool_freehand": "freehand",
    "tool_highlighter": "highlighter",
    "tool_line": "line",
    "tool_arrow": "arrow",
    "tool_rectangle": "rectangle",
    "tool_ellipse": "ellipse",
    "tool_stamp": "stamp_star",
    "tool_eraser": "eraser",
}
COLOR_SHORTCUTS = {f"color_{index + 1}": index for index in range(6)}
WIDTH_SHORTCUTS = {"width_down": -1, "width_up": 1}
COMMAND_SHORTCUTS = {
    "undo": CommandId.UNDO_DRAWING,
    "redo": CommandId.REDO_DRAWING,
    "clear": CommandId.CLEAR_DRAWING,
}
ESCAPE_ACTION = "escape"
TOOL_ACTIONS = {tool: action for action, tool in TOOL_SHORTCUTS.items()}
STAMP_NAMES = ("star", "heart", "check", "x", "exclamation")
ERASER_MODES = ("object", "pixel")


def next_stamp_tool(current_tool: str) -> str:
    """Pressing the stamp key again while a stamp is active moves to the
    next stamp; otherwise it starts from the first one."""
    if not current_tool.startswith("stamp_"):
        return f"stamp_{STAMP_NAMES[0]}"
    name = current_tool.removeprefix("stamp_")
    index = STAMP_NAMES.index(name) if name in STAMP_NAMES else -1
    return f"stamp_{STAMP_NAMES[(index + 1) % len(STAMP_NAMES)]}"


def next_eraser_mode(current_mode: str) -> str:
    index = ERASER_MODES.index(current_mode) if current_mode in ERASER_MODES else -1
    return ERASER_MODES[(index + 1) % len(ERASER_MODES)]


def qt_modifier_mask(modifiers: Qt.KeyboardModifier) -> int:
    mask = 0
    if modifiers & Qt.KeyboardModifier.ControlModifier:
        mask |= MOD_CONTROL
    if modifiers & Qt.KeyboardModifier.AltModifier:
        mask |= MOD_ALT
    if modifiers & Qt.KeyboardModifier.ShiftModifier:
        mask |= MOD_SHIFT
    return mask


def next_width(widths: tuple[int, ...], current: int, step: int) -> int:
    """Moves one preset up or down from `current`, clamped to the presets."""
    if step > 0:
        larger = [width for width in widths if width > current]
        return larger[0] if larger else widths[-1]
    smaller = [width for width in widths if width < current]
    return smaller[-1] if smaller else widths[0]


def with_shortcut(text: str, key: str) -> str:
    key = key.strip()
    return f"{text} ({key})" if key else text


def build_bindings(keys: dict[str, str]) -> dict[tuple[int, int], str]:
    """Maps (modifiers, vk) to an action name. Empty or unparsable keys are
    left unbound, and the first action wins if two share a key."""
    bindings: dict[tuple[int, int], str] = {}
    for name, text in keys.items():
        if not text.strip():
            continue
        parsed = parse_hotkey(text)
        if parsed is not None:
            bindings.setdefault(parsed, name)
    bindings[(0, VK_ESCAPE)] = ESCAPE_ACTION
    return bindings


class _KeyEmitter(QObject):
    action_triggered = Signal(str)


class DrawingShortcutService(Service):
    """Keyboard shortcuts for full-screen drawing mode.

    The overlay windows never take keyboard focus, so a low-level keyboard
    hook is used instead. It is installed only while overlay drawing mode is
    active, and only swallows keys bound to a drawing action; everything else
    reaches the foreground application unchanged.
    """

    def __init__(self, settings: DrawingShortcutSettings, dispatcher: CommandDispatcher, bus: EventBus) -> None:
        self.settings = settings
        self.dispatcher = dispatcher
        self.bus = bus
        self._bindings = build_bindings(settings.keys)
        self._hook = None
        self._drawing_active = False
        self._paused = False
        self._command_mode_active = False
        self._proc = LowLevelKeyboardProc(self._callback)
        self._subscriptions: list[Subscription] = []
        self._emitter = _KeyEmitter()
        self._emitter.action_triggered.connect(self._handle_action, Qt.ConnectionType.QueuedConnection)

    def start(self) -> None:
        if self._subscriptions:
            return
        self._subscriptions = [
            self.bus.subscribe("drawing.mode.changed", self._drawing_mode_changed),
            self.bus.subscribe("app.pause.changed", self._pause_changed),
            self.bus.subscribe("command_mode.active.changed", self._command_mode_changed),
            self.bus.subscribe("settings.saved", self._settings_saved),
        ]

    def stop(self) -> None:
        for subscription in self._subscriptions:
            self.bus.unsubscribe(subscription)
        self._subscriptions.clear()
        self._drawing_active = False
        self._uninstall_hook()

    def _drawing_mode_changed(self, event: Event) -> None:
        pass_through = bool(event.payload.get("pass_through", True))
        # Magnifier drawing keeps its own document and window focus; only the
        # full-screen overlay is driven from here.
        self._drawing_active = not pass_through and event.payload.get("scope", "overlay") == "overlay"
        self._update_hook()

    def _pause_changed(self, event: Event) -> None:
        self._paused = bool(event.payload.get("paused", False))
        self._update_hook()

    def _command_mode_changed(self, event: Event) -> None:
        self._command_mode_active = bool(event.payload.get("active", False))

    def _settings_saved(self, event: Event) -> None:
        settings = event.payload.get("settings")
        if isinstance(settings, Settings):
            self.settings = settings.drawing_shortcuts
            self._bindings = build_bindings(self.settings.keys)
            self._update_hook()

    def _update_hook(self) -> None:
        if self.settings.enabled and self._drawing_active and not self._paused:
            self._install_hook()
        else:
            self._uninstall_hook()

    def _install_hook(self) -> None:
        if self._hook:
            return
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, None, 0)
        if not self._hook:
            self.bus.publish("hotkey.failed", error="Drawing shortcut keyboard hook failed")

    def _uninstall_hook(self) -> None:
        if not self._hook:
            return
        user32.UnhookWindowsHookEx(self._hook)
        self._hook = None

    def _callback(self, code: int, wparam: int, lparam: int) -> int:
        if code == HC_ACTION and wparam in {WM_KEYDOWN, WM_SYSKEYDOWN} and not self._command_mode_active:
            data = ctypes.cast(lparam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            action = self._action_for_key(int(data.vkCode))
            if action is not None:
                self._emitter.action_triggered.emit(action)
                return 1
        return user32.CallNextHookEx(self._hook, code, wparam, lparam)

    def _action_for_key(self, vk_code: int) -> str | None:
        if key_down(VK_LWIN) or key_down(VK_RWIN):
            return None
        modifiers = 0
        if key_down(VK_CONTROL):
            modifiers |= MOD_CONTROL
        if key_down(VK_MENU):
            modifiers |= MOD_ALT
        if key_down(VK_SHIFT):
            modifiers |= MOD_SHIFT
        return self._bindings.get((modifiers, vk_code))

    def _handle_action(self, action: str) -> None:
        if not self._drawing_active or self._paused:
            return
        if action == ESCAPE_ACTION:
            if mouse_button_down(VK_LBUTTON):
                self.bus.publish("drawing.cancel")
            else:
                self.dispatcher.dispatch(CommandId.DRAWING_PASS_THROUGH)
        elif action in TOOL_SHORTCUTS:
            self.bus.publish("drawing.toolbar.tool.shortcut", tool=TOOL_SHORTCUTS[action])
        elif action in COLOR_SHORTCUTS:
            self.bus.publish("drawing.toolbar.color.select", index=COLOR_SHORTCUTS[action])
        elif action in WIDTH_SHORTCUTS:
            self.bus.publish("drawing.toolbar.width.step", step=WIDTH_SHORTCUTS[action])
        elif action in COMMAND_SHORTCUTS:
            self.dispatcher.dispatch(COMMAND_SHORTCUTS[action])

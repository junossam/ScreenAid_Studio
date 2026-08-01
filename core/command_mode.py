from __future__ import annotations

import ctypes

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout

from application.command_dispatcher import CommandDispatcher
from application.commands import CommandId
from config.settings import CommandModeSettings, Settings
from core.event_bus import Event, EventBus, Subscription
from core.hotkeys import KEY_NAME_TO_VK
from core.localization import tr
from core.service import Service
from utils.winapi import (
    HC_ACTION,
    KBDLLHOOKSTRUCT,
    LowLevelKeyboardProc,
    VK_ESCAPE,
    WH_KEYBOARD_LL,
    WM_KEYDOWN,
    WM_SYSKEYDOWN,
    user32,
)


COMMAND_MODE_COMMANDS = {
    "toggle_overlay": CommandId.TOGGLE_OVERLAY,
    "toggle_click_effects": CommandId.TOGGLE_CLICK_EFFECTS,
    "toggle_drawing": CommandId.TOGGLE_DRAWING_MODE,
    "pass_through": CommandId.DRAWING_PASS_THROUGH,
    "clear_drawing": CommandId.CLEAR_DRAWING,
    "undo_drawing": CommandId.UNDO_DRAWING,
    "redo_drawing": CommandId.REDO_DRAWING,
    "capture_region": CommandId.CAPTURE_REGION,
    "capture_last_region": CommandId.CAPTURE_LAST_REGION,
    "capture_monitor": CommandId.CAPTURE_CURRENT_MONITOR,
    "capture_virtual": CommandId.CAPTURE_VIRTUAL_SCREEN,
    "capture_window": CommandId.CAPTURE_ACTIVE_WINDOW,
    "pin_region": CommandId.PIN_REGION,
    "pin_last_capture": CommandId.PIN_LAST_CAPTURE,
    "live_region": CommandId.LIVE_REGION,
    "live_stop_all": CommandId.LIVE_STOP_ALL,
    "fullscreen_magnifier": CommandId.FULLSCREEN_MAGNIFIER,
    "open_settings": CommandId.OPEN_SETTINGS,
    "toggle_pause": CommandId.TOGGLE_PAUSE,
}

COMMAND_MODE_GROUPS = (
    ("command_mode.group.system", ("toggle_overlay", "toggle_click_effects", "toggle_pause")),
    ("command_mode.group.drawing", ("toggle_drawing", "pass_through", "clear_drawing", "undo_drawing", "redo_drawing")),
    (
        "command_mode.group.capture",
        ("capture_region", "capture_last_region", "capture_monitor", "capture_virtual", "capture_window"),
    ),
    ("command_mode.group.windows", ("pin_region", "pin_last_capture", "live_region", "live_stop_all", "fullscreen_magnifier")),
    ("command_mode.group.settings", ("open_settings",)),
)


class _KeyEmitter(QObject):
    key_pressed = Signal(int)


class _CommandModeHint(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        layout = QVBoxLayout(self)
        self.label = QLabel()
        self.label.setFont(QFont("Segoe UI", 10))
        self.label.setStyleSheet(
            "QLabel { background: rgba(32, 32, 32, 220); color: white; "
            "border-radius: 8px; padding: 10px 14px; }"
        )
        layout.addWidget(self.label)

    def show_keys(self, text: str) -> None:
        self.label.setText(text)
        self.adjustSize()
        screen = QApplication.primaryScreen()
        if screen is not None:
            rect = screen.availableGeometry()
            self.move(rect.center().x() - self.width() // 2, rect.bottom() - self.height() - 48)
        self.show()


class CommandModeService(Service):
    def __init__(self, settings: CommandModeSettings, dispatcher: CommandDispatcher, bus: EventBus) -> None:
        self.settings = settings
        self.dispatcher = dispatcher
        self.bus = bus
        self._hook = None
        self._active = False
        self._proc = LowLevelKeyboardProc(self._callback)
        self._subscriptions: list[Subscription] = []
        self._emitter = _KeyEmitter()
        self._emitter.key_pressed.connect(self._handle_key, Qt.ConnectionType.QueuedConnection)
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._deactivate)
        self._hint = _CommandModeHint()

    def start(self) -> None:
        if self._subscriptions:
            return
        self._subscriptions = [
            self.bus.subscribe("command_mode.open", self._open),
            self.bus.subscribe("settings.saved", self._settings_saved),
        ]
        self._install_hook()

    def stop(self) -> None:
        for subscription in self._subscriptions:
            self.bus.unsubscribe(subscription)
        self._subscriptions.clear()
        self._deactivate()
        self._uninstall_hook()
        self._hint.close()

    def _open(self, _event: Event) -> None:
        if not self.settings.enabled:
            return
        self._activate()

    def _activate(self) -> None:
        if not self._hook:
            self._install_hook()
        if not self._hook:
            return
        self._active = True
        if self.settings.show_hint:
            self._hint.show_keys(self._hint_text())
        self._timer.start(self.settings.timeout_ms)

    def _deactivate(self) -> None:
        self._timer.stop()
        self._hint.hide()
        self._active = False

    def _install_hook(self) -> None:
        if self._hook:
            return
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, None, 0)
        if not self._hook:
            self.bus.publish("hotkey.failed", error="Command mode keyboard hook failed")

    def _uninstall_hook(self) -> None:
        if not self._hook:
            return
        user32.UnhookWindowsHookEx(self._hook)
        self._hook = None

    def _callback(self, code: int, wparam: int, lparam: int) -> int:
        if self._active and code == HC_ACTION and wparam in {WM_KEYDOWN, WM_SYSKEYDOWN}:
            data = ctypes.cast(lparam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            self._emitter.key_pressed.emit(int(data.vkCode))
            return 1
        return user32.CallNextHookEx(self._hook, code, wparam, lparam)

    def _handle_key(self, vk_code: int) -> None:
        if vk_code == VK_ESCAPE:
            self._deactivate()
            return
        command = self._command_for_vk(vk_code)
        self._deactivate()
        if command is not None:
            self.dispatcher.dispatch(command)

    def _command_for_vk(self, vk_code: int) -> CommandId | None:
        for name, text in self.settings.keys.items():
            if parse_command_key(text) == vk_code:
                return COMMAND_MODE_COMMANDS.get(name)
        return None

    def _settings_saved(self, event: Event) -> None:
        settings = event.payload.get("settings")
        if isinstance(settings, Settings):
            self.settings = settings.command_mode
            self._deactivate()

    def _hint_text(self) -> str:
        lines = [tr("command_mode.title")]
        for group_title, names in COMMAND_MODE_GROUPS:
            entries = [self._hint_entry(name) for name in names]
            entries = [entry for entry in entries if entry]
            if entries:
                lines.append(f"{tr(group_title)}: {'   '.join(entries)}")
        lines.append(f"Esc {tr('command_mode.cancel')}")
        return "\n".join(lines)

    def _hint_entry(self, name: str) -> str:
        key = self.settings.keys.get(name, "")
        if not key.strip():
            return ""
        return f"{key.upper()} {tr(f'hotkey.{name}')}"


def parse_command_key(text: str) -> int | None:
    key = text.strip().upper()
    if not key:
        return None
    return KEY_NAME_TO_VK.get(key)

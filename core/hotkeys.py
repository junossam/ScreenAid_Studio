from __future__ import annotations

import ctypes

from PySide6.QtCore import QAbstractNativeEventFilter, QByteArray, QCoreApplication

from application.command_dispatcher import CommandDispatcher
from application.commands import CommandId
from config.settings import HotkeySettings, Settings
from core.event_bus import Event, Subscription
from utils.winapi import WM_HOTKEY, user32

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
HOTKEY_COMMAND_MODE = 1
HOTKEY_TOGGLE_CLICK_EFFECTS = 2
VK_SPACE = 0x20
VK_A = 0x41
VK_B = 0x42
VK_C = 0x43
VK_D = 0x44
VK_E = 0x45
VK_F = 0x46
VK_G = 0x47
VK_I = 0x49
VK_J = 0x4A
VK_K = 0x4B
VK_P = 0x50
VK_O = 0x4F
VK_Q = 0x51
VK_R = 0x52
VK_S = 0x53
VK_X = 0x58
VK_L = 0x4C
VK_M = 0x4D
VK_V = 0x56
VK_W = 0x57
VK_Y = 0x59
VK_Z = 0x5A

HOTKEY_BINDINGS = (
    (HOTKEY_COMMAND_MODE, "command_mode", CommandId.OPEN_COMMAND_MODE, "Ctrl+Alt+A"),
    (HOTKEY_TOGGLE_CLICK_EFFECTS, "toggle_click_effects", CommandId.TOGGLE_CLICK_EFFECTS, "Ctrl+Alt+E"),
)
DEFAULT_HOTKEYS = {name: default for _hotkey_id, name, _command, default in HOTKEY_BINDINGS}
HOTKEY_COMMANDS = {hotkey_id: command for hotkey_id, _name, command, _default in HOTKEY_BINDINGS}
KEY_NAME_TO_VK = {
    "A": VK_A,
    "B": VK_B,
    "C": VK_C,
    "D": VK_D,
    "E": VK_E,
    "F": VK_F,
    "G": VK_G,
    "I": VK_I,
    "J": VK_J,
    "K": VK_K,
    "O": VK_O,
    "P": VK_P,
    "Q": VK_Q,
    "R": VK_R,
    "S": VK_S,
    "X": VK_X,
    "L": VK_L,
    "M": VK_M,
    "V": VK_V,
    "W": VK_W,
    "Y": VK_Y,
    "Z": VK_Z,
    "SPACE": VK_SPACE,
}


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_size_t),
        ("lParam", ctypes.c_ssize_t),
        ("time", ctypes.c_uint),
        ("pt_x", ctypes.c_long),
        ("pt_y", ctypes.c_long),
    ]


class HotkeyManager(QAbstractNativeEventFilter):
    def __init__(self, dispatcher: CommandDispatcher, hotkeys: HotkeySettings, bus=None) -> None:
        super().__init__()
        self.dispatcher = dispatcher
        self.bus = bus
        self.hotkeys = hotkeys
        self._registered: list[int] = []
        self._failed: list[str] = []
        self._subscription: Subscription | None = None

    def start(self) -> None:
        app = QCoreApplication.instance()
        if app:
            app.installNativeEventFilter(self)
        if self.bus is not None and self._subscription is None:
            self._subscription = self.bus.subscribe("settings.saved", self._settings_saved)
        self._register_all()

    def stop(self) -> None:
        self._unregister_all()
        self._failed.clear()
        if self.bus is not None and self._subscription is not None:
            self.bus.unsubscribe(self._subscription)
            self._subscription = None
        app = QCoreApplication.instance()
        if app:
            app.removeNativeEventFilter(self)

    def nativeEventFilter(self, _event_type: QByteArray, message: int):
        msg = ctypes.cast(int(message), ctypes.POINTER(MSG)).contents
        if msg.message != WM_HOTKEY:
            return False, 0
        command = HOTKEY_COMMANDS.get(msg.wParam)
        if command is not None:
            self.dispatcher.dispatch(command)
            return True, 0
        return False, 0

    def _register_all(self) -> None:
        for hotkey_id, name, _command, default in HOTKEY_BINDINGS:
            text = self.hotkeys.values.get(name, default)
            if not text.strip():
                continue
            parsed = parse_hotkey(text)
            if parsed is None:
                self._failed.append(f"{name}={text}")
                continue
            modifiers, key = parsed
            self._register(hotkey_id, modifiers, key)

    def _unregister_all(self) -> None:
        for hotkey_id in self._registered:
            user32.UnregisterHotKey(None, hotkey_id)
        self._registered.clear()

    def _settings_saved(self, event: Event) -> None:
        settings = event.payload.get("settings")
        if not isinstance(settings, Settings):
            return
        self.hotkeys = settings.hotkeys
        self._unregister_all()
        self._failed.clear()
        self._register_all()

    def _register(self, hotkey_id: int, modifiers: int, key: int) -> None:
        if user32.RegisterHotKey(None, hotkey_id, modifiers, key):
            self._registered.append(hotkey_id)
        else:
            message = f"id={hotkey_id} modifiers={modifiers} key={key}"
            self._failed.append(message)
            if self.bus is not None:
                self.bus.publish("hotkey.failed", error=message)


def parse_hotkey(text: str) -> tuple[int, int] | None:
    parts = [part.strip().upper() for part in text.split("+") if part.strip()]
    if not parts:
        return None
    modifiers = 0
    key = 0
    for part in parts:
        if part == "CTRL" or part == "CONTROL":
            modifiers |= MOD_CONTROL
        elif part == "ALT":
            modifiers |= MOD_ALT
        elif part in KEY_NAME_TO_VK:
            key = KEY_NAME_TO_VK[part]
        else:
            return None
    if key == 0:
        return None
    return modifiers, key

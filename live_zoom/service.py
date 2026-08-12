from __future__ import annotations

import ctypes

from config.settings import LiveZoomSettings
from core.event_bus import Event, EventBus, Subscription
from core.service import Service
from live_zoom.transform import clamp, fullscreen_offset
from utils.winapi import (
    HC_ACTION,
    KBDLLHOOKSTRUCT,
    MSLLHOOKSTRUCT,
    VK_ESCAPE,
    WH_KEYBOARD_LL,
    WH_MOUSE_LL,
    WM_KEYDOWN,
    WM_MOUSEMOVE,
    WM_MOUSEWHEEL,
    WM_SYSKEYDOWN,
    LowLevelKeyboardProc,
    LowLevelMouseProc,
    cursor_pos,
    mag_initialize,
    mag_set_fullscreen_transform,
    mag_uninitialize,
    monitor_info_from_point,
    signed_hiword,
    user32,
    virtual_desktop_rect,
)


class LiveZoomService(Service):
    """Zoomit-style live screen zoom on top of the Magnification API's
    full-screen transform (utils.winapi's Mag* bindings). Panning follows the
    cursor via WM_MOUSEMOVE on the same low-level hook used for the wheel, so
    updates are driven by real pointer movement rather than a fixed-interval
    poll. Escape exits.

    The mouse/keyboard hooks are only installed while zoom is active, so
    normal scrolling/Escape behavior elsewhere is untouched, and they coexist
    safely with mouse.hook.GlobalMouseHook's own always-on WH_MOUSE_LL hook -
    Windows chains multiple low-level hooks via CallNextHookEx.

    The real system cursor is left alone (not hidden/replaced): it doesn't
    visually track the magnification transform on every system, which looks
    a little off, but it always marks the real, accurate click target.
    """

    def __init__(self, settings: LiveZoomSettings, bus: EventBus) -> None:
        self.settings = settings
        self.bus = bus
        self._active = False
        self._scale = settings.default_scale
        self._initialized = False
        self._mouse_hook = None
        self._keyboard_hook = None
        self._mouse_proc = LowLevelMouseProc(self._mouse_callback)
        self._keyboard_proc = LowLevelKeyboardProc(self._keyboard_callback)
        self._subscriptions: list[Subscription] = []

    def start(self) -> None:
        if self._subscriptions:
            return
        self._subscriptions = [
            self.bus.subscribe("live_zoom.toggle", self._toggle),
            self.bus.subscribe("app.pause.changed", self._pause_changed),
            self.bus.subscribe("settings.saved", self._settings_saved),
        ]

    def stop(self) -> None:
        for subscription in self._subscriptions:
            self.bus.unsubscribe(subscription)
        self._subscriptions.clear()
        if self._active:
            self._deactivate()
        if self._initialized:
            mag_uninitialize()
            self._initialized = False

    def is_active(self) -> bool:
        return self._active

    def _toggle(self, _event: Event) -> None:
        if not self.settings.enabled:
            return
        if self._active:
            self._deactivate()
        else:
            self._activate()

    def _activate(self) -> None:
        if not self._initialized:
            self._initialized = mag_initialize()
            if not self._initialized:
                self.bus.publish("live_zoom.failed", error="MagInitialize failed")
                return
        self._active = True
        self._scale = clamp(self.settings.default_scale, self.settings.min_scale, self.settings.max_scale)
        self._mouse_hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._mouse_proc, None, 0)
        self._keyboard_hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._keyboard_proc, None, 0)
        self._apply_transform_at_cursor()

    def _deactivate(self) -> None:
        self._active = False
        mag_set_fullscreen_transform(1.0, 0, 0)
        if self._mouse_hook:
            user32.UnhookWindowsHookEx(self._mouse_hook)
            self._mouse_hook = None
        if self._keyboard_hook:
            user32.UnhookWindowsHookEx(self._keyboard_hook)
            self._keyboard_hook = None

    def _apply_transform_at_cursor(self) -> None:
        point = cursor_pos()
        self._apply_transform(point.x, point.y)

    def _apply_transform(self, anchor_x: int, anchor_y: int) -> None:
        monitor_rect = self._monitor_rect_at(anchor_x, anchor_y)
        x_offset, y_offset = fullscreen_offset(anchor_x, anchor_y, monitor_rect, self._scale)
        mag_set_fullscreen_transform(self._scale, x_offset, y_offset)

    @staticmethod
    def _monitor_rect_at(x: int, y: int) -> tuple[int, int, int, int]:
        info = monitor_info_from_point(x, y)
        if info is None:
            return virtual_desktop_rect()
        rect = info.rcMonitor
        return rect.left, rect.top, rect.right, rect.bottom

    def _mouse_callback(self, code: int, wparam: int, lparam: int) -> int:
        if code == HC_ACTION and self._active:
            if wparam == WM_MOUSEWHEEL:
                data = ctypes.cast(lparam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                steps = signed_hiword(data.mouseData) / 120
                if steps:
                    self._scale = clamp(
                        self._scale + steps * self.settings.wheel_step,
                        self.settings.min_scale,
                        self.settings.max_scale,
                    )
                    self._apply_transform(data.pt.x, data.pt.y)
                    return 1
            elif wparam == WM_MOUSEMOVE:
                # Not consumed (falls through to CallNextHookEx below) -
                # normal pointer movement everywhere else must keep working.
                data = ctypes.cast(lparam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                self._apply_transform(data.pt.x, data.pt.y)
        return user32.CallNextHookEx(self._mouse_hook, code, wparam, lparam)

    def _keyboard_callback(self, code: int, wparam: int, lparam: int) -> int:
        if code == HC_ACTION and wparam in (WM_KEYDOWN, WM_SYSKEYDOWN) and self._active:
            data = ctypes.cast(lparam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            if data.vkCode == VK_ESCAPE:
                self._deactivate()
                return 1
        return user32.CallNextHookEx(self._keyboard_hook, code, wparam, lparam)

    def _pause_changed(self, event: Event) -> None:
        if self._active and bool(event.payload.get("paused", False)):
            self._deactivate()

    def _settings_saved(self, event: Event) -> None:
        settings = event.payload.get("settings")
        if settings is None:
            return
        self.settings = settings.live_zoom
        if not self.settings.enabled and self._active:
            self._deactivate()

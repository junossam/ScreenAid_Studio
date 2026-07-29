from __future__ import annotations

import ctypes

from PySide6.QtCore import QObject, Qt, Signal

from core.event_bus import EventBus
from core.service import Service
from mouse.events import MouseEvent, MouseEventType
from utils.winapi import (
    HC_ACTION,
    LLMHF_INJECTED,
    LLMHF_LOWER_IL_INJECTED,
    LowLevelMouseProc,
    MSLLHOOKSTRUCT,
    WH_MOUSE_LL,
    WM_LBUTTONDOWN,
    WM_LBUTTONUP,
    WM_MBUTTONDOWN,
    WM_MBUTTONUP,
    WM_MOUSEMOVE,
    WM_MOUSEWHEEL,
    WM_MOUSEHWHEEL,
    WM_RBUTTONDOWN,
    WM_RBUTTONUP,
    signed_hiword,
    user32,
    window_from_point,
)


class _MouseEventEmitter(QObject):
    mouse_event = Signal(object)


class GlobalMouseHook(Service):
    def __init__(self, bus: EventBus) -> None:
        super().__init__()
        self.bus = bus
        self._hook = None
        self._proc = LowLevelMouseProc(self._callback)
        self._left_pressed = False
        self._overlay_hwnd = 0
        self._block_overlay_input = False
        self._blocking_suspended = False
        self._input_exclusions: dict[str, tuple[int, int, int, int]] = {}
        self._subscriptions = []
        self._emitter = _MouseEventEmitter()
        self._emitter.mouse_event.connect(self._publish_mouse_event, Qt.ConnectionType.QueuedConnection)

    def start(self) -> None:
        if self._hook:
            return
        self._hook = user32.SetWindowsHookExW(WH_MOUSE_LL, self._proc, None, 0)
        if not self._hook:
            raise RuntimeError("SetWindowsHookExW(WH_MOUSE_LL) failed")
        if not self._subscriptions:
            self._subscriptions = [
                self.bus.subscribe("overlay.input_mode.changed", self._overlay_input_mode_changed),
                self.bus.subscribe("drawing.mode.changed", self._drawing_mode_changed),
                self.bus.subscribe("mouse.input_exclusion.changed", self._input_exclusion_changed),
                self.bus.subscribe("mouse.blocking.suspended", self._blocking_suspended_changed),
            ]

    def stop(self) -> None:
        for subscription in self._subscriptions:
            self.bus.unsubscribe(subscription)
        self._subscriptions.clear()
        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None

    def _callback(self, code: int, wparam: int, lparam: int) -> int:
        if code == HC_ACTION:
            data = ctypes.cast(lparam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
            event = self._to_event(wparam, data)
            if event and self._should_emit(event):
                self._emitter.mouse_event.emit(event)
            if event and self._should_block(event):
                return 1
        return user32.CallNextHookEx(self._hook, code, wparam, lparam)

    def _publish_mouse_event(self, event: MouseEvent) -> None:
        self.bus.publish("mouse.event", event=event)

    def _to_event(self, wparam: int, data: MSLLHOOKSTRUCT) -> MouseEvent | None:
        event_type = {
            WM_LBUTTONDOWN: MouseEventType.LEFT_DOWN,
            WM_LBUTTONUP: MouseEventType.LEFT_UP,
            WM_RBUTTONDOWN: MouseEventType.RIGHT_DOWN,
            WM_RBUTTONUP: MouseEventType.RIGHT_UP,
            WM_MBUTTONDOWN: MouseEventType.MIDDLE_DOWN,
            WM_MBUTTONUP: MouseEventType.MIDDLE_UP,
            WM_MOUSEMOVE: MouseEventType.MOVE,
            WM_MOUSEWHEEL: MouseEventType.WHEEL,
            WM_MOUSEHWHEEL: MouseEventType.HWHEEL,
        }.get(wparam)
        if event_type is None:
            return None
        return MouseEvent(
            event_type=event_type,
            x=data.pt.x,
            y=data.pt.y,
            timestamp_ms=data.time,
            wheel_delta=signed_hiword(data.mouseData)
            if event_type in {MouseEventType.WHEEL, MouseEventType.HWHEEL}
            else 0,
            injected=bool(data.flags & (LLMHF_INJECTED | LLMHF_LOWER_IL_INJECTED)),
        )

    def _should_emit(self, event: MouseEvent) -> bool:
        if self._blocking_suspended or self._is_inside_input_exclusion(event.x, event.y):
            self._update_pressed_state(event)
            return False
        if event.event_type == MouseEventType.LEFT_DOWN:
            self._left_pressed = True
            return True
        if event.event_type == MouseEventType.LEFT_UP:
            self._left_pressed = False
            return True
        if event.event_type == MouseEventType.MOVE:
            return self._left_pressed
        return True

    def _update_pressed_state(self, event: MouseEvent) -> None:
        if event.event_type == MouseEventType.LEFT_DOWN:
            self._left_pressed = True
        elif event.event_type == MouseEventType.LEFT_UP:
            self._left_pressed = False

    def _should_block(self, event: MouseEvent) -> bool:
        if event.injected or not self._block_overlay_input or self._blocking_suspended:
            return False
        if event.event_type == MouseEventType.MOVE:
            return False
        if self._is_inside_input_exclusion(event.x, event.y):
            return False
        if self._overlay_hwnd and window_from_point(event.x, event.y) == self._overlay_hwnd:
            return True
        return event.event_type in {
            MouseEventType.LEFT_DOWN,
            MouseEventType.LEFT_UP,
            MouseEventType.RIGHT_DOWN,
            MouseEventType.RIGHT_UP,
            MouseEventType.MIDDLE_DOWN,
            MouseEventType.MIDDLE_UP,
            MouseEventType.WHEEL,
            MouseEventType.HWHEEL,
        }

    def _overlay_input_mode_changed(self, event) -> None:
        self._overlay_hwnd = int(event.payload.get("hwnd", 0))
        self._block_overlay_input = not bool(event.payload.get("pass_through", True))

    def _drawing_mode_changed(self, event) -> None:
        self._block_overlay_input = not bool(event.payload.get("pass_through", True))

    def _input_exclusion_changed(self, event) -> None:
        source = str(event.payload.get("source", ""))
        rect = event.payload.get("rect")
        if not source:
            return
        if rect is None:
            self._input_exclusions.pop(source, None)
            return
        left, top, right, bottom = rect
        self._input_exclusions[source] = (int(left), int(top), int(right), int(bottom))

    def _blocking_suspended_changed(self, event) -> None:
        self._blocking_suspended = bool(event.payload.get("suspended", False))

    def _is_inside_input_exclusion(self, x: int, y: int) -> bool:
        for left, top, right, bottom in self._input_exclusions.values():
            if left <= x < right and top <= y < bottom:
                return True
        return False

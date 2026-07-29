from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from PySide6.QtCore import QPoint, QRect

from mouse.events import MouseEvent, MouseEventType


class ClickEffectType(str, Enum):
    LEFT = "left"
    RIGHT = "right"
    DOUBLE = "double"
    MIDDLE = "middle"
    BOTH = "both"
    WHEEL_UP = "wheel_up"
    WHEEL_DOWN = "wheel_down"
    WHEEL_LEFT = "wheel_left"
    WHEEL_RIGHT = "wheel_right"


class ClickEffectState(str, Enum):
    PRESSED = "pressed"
    RELEASED = "released"
    FADING = "fading"


@dataclass
class ClickButtonTracker:
    double_click_ms: int = 500
    double_click_distance: int = 6
    left_pressed: bool = False
    right_pressed: bool = False
    middle_pressed: bool = False
    _last_left_down_ms: int | None = None
    _last_left_down_x: int | None = None
    _last_left_down_y: int | None = None
    _last_middle_drag_ms: int | None = None

    def apply(self, event: MouseEvent) -> ClickEffectType | None:
        match event.event_type:
            case MouseEventType.LEFT_DOWN:
                double_clicked = self._is_left_double_click(event)
                self.left_pressed = True
                self._last_left_down_ms = event.timestamp_ms
                self._last_left_down_x = event.x
                self._last_left_down_y = event.y
                if self.right_pressed:
                    return ClickEffectType.BOTH
                return ClickEffectType.DOUBLE if double_clicked else ClickEffectType.LEFT
            case MouseEventType.RIGHT_DOWN:
                self.right_pressed = True
                return ClickEffectType.BOTH if self.left_pressed else ClickEffectType.RIGHT
            case MouseEventType.MIDDLE_DOWN:
                self.middle_pressed = True
                self._last_middle_drag_ms = event.timestamp_ms
                return ClickEffectType.MIDDLE
            case MouseEventType.LEFT_UP:
                self.left_pressed = False
            case MouseEventType.RIGHT_UP:
                self.right_pressed = False
            case MouseEventType.MIDDLE_UP:
                self.middle_pressed = False
                self._last_middle_drag_ms = None
            case MouseEventType.MOVE:
                if self.middle_pressed and self._is_middle_drag_tick(event):
                    self._last_middle_drag_ms = event.timestamp_ms
                    return ClickEffectType.MIDDLE
            case MouseEventType.WHEEL:
                return ClickEffectType.WHEEL_UP if event.wheel_delta > 0 else ClickEffectType.WHEEL_DOWN
            case MouseEventType.HWHEEL:
                return ClickEffectType.WHEEL_RIGHT if event.wheel_delta > 0 else ClickEffectType.WHEEL_LEFT
            case _:
                return None
        return None

    def reset(self) -> None:
        self.left_pressed = False
        self.right_pressed = False
        self.middle_pressed = False
        self._last_left_down_ms = None
        self._last_left_down_x = None
        self._last_left_down_y = None
        self._last_middle_drag_ms = None

    def _is_left_double_click(self, event: MouseEvent) -> bool:
        if self._last_left_down_ms is None:
            return False
        if event.timestamp_ms - self._last_left_down_ms > self.double_click_ms:
            return False
        if self._last_left_down_x is None or self._last_left_down_y is None:
            return False
        return (
            abs(event.x - self._last_left_down_x) <= self.double_click_distance
            and abs(event.y - self._last_left_down_y) <= self.double_click_distance
        )

    def _is_middle_drag_tick(self, event: MouseEvent) -> bool:
        if self._last_middle_drag_ms is None:
            return True
        return event.timestamp_ms - self._last_middle_drag_ms >= 80


@dataclass
class ClickEffect:
    effect_type: ClickEffectType
    center: QPoint
    radius: int
    pressed_radius: int
    color: str
    outline_color: str
    width: int
    created_ms: int
    hold_until_ms: int
    fade_ms: int
    state: ClickEffectState = ClickEffectState.PRESSED
    released_ms: int | None = None
    opacity: float = 1.0

    def bounds(self) -> QRect:
        max_radius = max(self.radius, self.pressed_radius)
        pad = self.width + 20
        size = max_radius * 2 + pad * 2
        return QRect(
            self.center.x() - max_radius - pad,
            self.center.y() - max_radius - pad,
            size,
            size,
        )

    def current_radius(self) -> int:
        return self.pressed_radius if self.state == ClickEffectState.PRESSED else self.radius

    def release(self, now_ms: int) -> None:
        self.state = ClickEffectState.RELEASED
        self.released_ms = now_ms
        self.hold_until_ms = now_ms

    def update(self, now_ms: int) -> bool:
        if self.state == ClickEffectState.PRESSED and now_ms < self.hold_until_ms:
            return True
        if self.released_ms is None:
            self.released_ms = now_ms
        self.state = ClickEffectState.FADING
        elapsed = max(0, now_ms - self.released_ms)
        if elapsed >= self.fade_ms:
            self.opacity = 0.0
            return False
        self.opacity = 1.0 - elapsed / max(1, self.fade_ms)
        return True

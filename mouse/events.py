from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MouseEventType(str, Enum):
    LEFT_DOWN = "left_down"
    LEFT_UP = "left_up"
    RIGHT_DOWN = "right_down"
    RIGHT_UP = "right_up"
    MIDDLE_DOWN = "middle_down"
    MIDDLE_UP = "middle_up"
    MOVE = "move"
    WHEEL = "wheel"
    HWHEEL = "hwheel"


@dataclass(frozen=True, slots=True)
class MouseEvent:
    event_type: MouseEventType
    x: int
    y: int
    timestamp_ms: int
    wheel_delta: int = 0
    injected: bool = False

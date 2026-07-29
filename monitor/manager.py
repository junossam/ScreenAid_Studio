from __future__ import annotations

import ctypes
from dataclasses import dataclass

from PySide6.QtCore import QRect

from utils.winapi import MONITOR_DEFAULTTONEAREST, POINT, user32


@dataclass(frozen=True)
class MonitorInfo:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


def monitor_from_point(x: int, y: int) -> int:
    return user32.MonitorFromPoint(POINT(x, y), MONITOR_DEFAULTTONEAREST)


def virtual_screen_rect() -> MonitorInfo:
    return MonitorInfo(
        left=user32.GetSystemMetrics(76),
        top=user32.GetSystemMetrics(77),
        right=user32.GetSystemMetrics(76) + user32.GetSystemMetrics(78),
        bottom=user32.GetSystemMetrics(77) + user32.GetSystemMetrics(79),
    )


def virtual_screen_qrect() -> QRect:
    rect = virtual_screen_rect()
    return QRect(rect.left, rect.top, rect.width, rect.height)

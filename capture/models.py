from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from PySide6.QtCore import QRect
from PySide6.QtGui import QImage


class CaptureType(str, Enum):
    REGION = "region"
    VIRTUAL_SCREEN = "virtual_screen"
    CURRENT_MONITOR = "current_monitor"
    ACTIVE_WINDOW = "active_window"


@dataclass(frozen=True, slots=True)
class CaptureRequest:
    capture_type: CaptureType
    rect: QRect
    include_annotations: bool = True
    include_cursor: bool = False


@dataclass(slots=True)
class CaptureResult:
    capture_type: CaptureType
    image: QImage
    virtual_rect: QRect
    width: int
    height: int
    dpi_x: int
    dpi_y: int
    captured_at: datetime
    source_monitor_id: str | None = None
    source_window_handle: int | None = None
    includes_annotations: bool = False
    includes_cursor: bool = False

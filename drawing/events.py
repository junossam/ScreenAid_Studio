from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPoint


@dataclass(frozen=True, slots=True)
class PointerEvent:
    position: QPoint
    timestamp_ms: int
    pressure: float = 1.0
    shift: bool = False
    alt: bool = False

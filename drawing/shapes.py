from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

from PySide6.QtCore import QPoint, QRect


class ShapeType(str, Enum):
    FREEHAND = "freehand"
    HIGHLIGHTER = "highlighter"
    LINE = "line"
    ARROW = "arrow"
    RECTANGLE = "rectangle"
    ELLIPSE = "ellipse"
    STAMP = "stamp"
    ERASER = "eraser"


@dataclass(slots=True)
class Shape:
    shape_type: ShapeType
    points: list[QPoint]
    stroke_color: str
    stroke_width: int
    stroke_style: str = "solid"
    stroke_opacity: int = 255
    fill_color: str | None = None
    fill_opacity: int = 0
    stamp_name: str = "star"
    shape_id: str = field(default_factory=lambda: uuid4().hex)
    z_index: int = 0
    is_visible: bool = True

    def bounds(self) -> QRect:
        if not self.points:
            return QRect()
        xs = [point.x() for point in self.points]
        ys = [point.y() for point in self.points]
        pad = self.stroke_width + 4
        return QRect(
            min(xs) - pad,
            min(ys) - pad,
            max(xs) - min(xs) + pad * 2,
            max(ys) - min(ys) + pad * 2,
        )

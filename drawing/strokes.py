from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import QPoint, QRect


@dataclass
class Stroke:
    color: str
    width: int
    points: list[QPoint] = field(default_factory=list)

    def bounds(self) -> QRect:
        if not self.points:
            return QRect()
        xs = [point.x() for point in self.points]
        ys = [point.y() for point in self.points]
        pad = self.width + 2
        return QRect(min(xs) - pad, min(ys) - pad, max(xs) - min(xs) + pad * 2, max(ys) - min(ys) + pad * 2)


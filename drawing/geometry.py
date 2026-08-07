from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainterPath

from drawing.shapes import Shape, ShapeType


def curve_path(points: list) -> QPainterPath:
    path = QPainterPath(points[0])
    if len(points) == 2:
        path.lineTo(points[1])
        return path
    for index in range(1, len(points) - 1):
        current = points[index]
        next_point = points[index + 1]
        mid = (current + next_point) / 2
        path.quadTo(current, mid)
    path.lineTo(points[-1])
    return path


def shape_stroke_path(shape: Shape) -> QPainterPath:
    """A path following a shape's stroke, for lines/curves that have no interior area."""
    if shape.shape_type in {ShapeType.FREEHAND, ShapeType.HIGHLIGHTER, ShapeType.ERASER}:
        return curve_path(shape.points)
    path = QPainterPath(shape.points[0])
    path.lineTo(shape.points[1])
    return path


def shape_fill_path(shape: Shape) -> QPainterPath:
    """A closed path for shapes with an interior area (clicking inside counts as a hit)."""
    rect = QRectF(shape.points[0], shape.points[1]).normalized()
    path = QPainterPath()
    if shape.shape_type == ShapeType.ELLIPSE:
        path.addEllipse(rect)
    else:
        path.addRect(rect)
    return path

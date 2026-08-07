from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QPointF, QRect
from PySide6.QtGui import QPainterPathStroker

from drawing.geometry import shape_fill_path, shape_stroke_path
from drawing.shapes import Shape, ShapeType

MIN_ERASE_HIT_WIDTH = 12


class DrawingDocument:
    def __init__(self) -> None:
        self._shapes: list[Shape] = []
        self._redo_stack: list[Shape] = []
        self._next_z_index = 0

    def add_shape(self, shape: Shape) -> QRect:
        shape.z_index = self._next_z_index
        self._next_z_index += 1
        self._shapes.append(shape)
        self._redo_stack.clear()
        return shape.bounds()

    def clear(self) -> QRect:
        dirty = QRect()
        for shape in self._shapes:
            dirty = dirty.united(shape.bounds())
        self._shapes.clear()
        self._redo_stack.clear()
        return dirty

    def undo(self) -> QRect:
        if not self._shapes:
            return QRect()
        shape = self._shapes.pop()
        self._redo_stack.append(shape)
        return shape.bounds()

    def redo(self) -> QRect:
        if not self._redo_stack:
            return QRect()
        shape = self._redo_stack.pop()
        self._shapes.append(shape)
        return shape.bounds()

    def erase_at(self, point) -> QRect:
        click = QPointF(point)
        for shape in sorted(self._shapes, key=lambda item: item.z_index, reverse=True):
            if not shape.bounds().contains(point):
                continue
            if not self._hit_test(shape, click):
                continue
            self._shapes.remove(shape)
            self._redo_stack.clear()
            return shape.bounds()
        return QRect()

    @staticmethod
    def _hit_test(shape: Shape, click: QPointF) -> bool:
        if shape.shape_type == ShapeType.STAMP or len(shape.points) < 2:
            # Bounds already matched above; stamps are compact icon shapes
            # where the bounding box is a good enough hit region.
            return True
        if shape.shape_type in {ShapeType.RECTANGLE, ShapeType.ELLIPSE}:
            return shape_fill_path(shape).contains(click)
        stroker = QPainterPathStroker()
        stroker.setWidth(max(shape.stroke_width, MIN_ERASE_HIT_WIDTH))
        return stroker.createStroke(shape_stroke_path(shape)).contains(click)

    def shapes(self) -> Iterable[Shape]:
        return tuple(sorted(self._shapes, key=lambda shape: shape.z_index))

    def is_empty(self) -> bool:
        return not self._shapes

    def can_redo(self) -> bool:
        return bool(self._redo_stack)

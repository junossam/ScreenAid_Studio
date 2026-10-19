from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRect
from PySide6.QtGui import QPainterPathStroker

from drawing.geometry import shape_fill_path, shape_stroke_path
from drawing.shapes import Shape, ShapeType

MIN_ERASE_HIT_WIDTH = 12


@dataclass(slots=True)
class _ClearRecord:
    """Undo history entry for "clear all": the shapes that were removed."""

    shapes: list[Shape]


_HistoryEntry = Shape | _ClearRecord


class DrawingDocument:
    def __init__(self) -> None:
        self._shapes: list[Shape] = []
        self._history: list[_HistoryEntry] = []
        self._redo_stack: list[_HistoryEntry] = []
        self._next_z_index = 0

    def add_shape(self, shape: Shape) -> QRect:
        shape.z_index = self._next_z_index
        self._next_z_index += 1
        self._shapes.append(shape)
        self._history.append(shape)
        self._redo_stack.clear()
        return shape.bounds()

    def clear(self) -> QRect:
        """Removes every shape as one undoable step."""
        if not self._shapes:
            return QRect()
        dirty = self._bounds_of(self._shapes)
        self._history.append(_ClearRecord(list(self._shapes)))
        self._shapes.clear()
        self._redo_stack.clear()
        return dirty

    def reset(self) -> QRect:
        """Discards all shapes and the undo/redo history."""
        dirty = self._bounds_of(self._shapes)
        self._shapes.clear()
        self._history.clear()
        self._redo_stack.clear()
        return dirty

    def undo(self) -> QRect:
        while self._history:
            entry = self._history.pop()
            if isinstance(entry, _ClearRecord):
                self._shapes.extend(entry.shapes)
                self._redo_stack.append(entry)
                return self._bounds_of(entry.shapes)
            index = self._index_of(entry)
            if index is not None:
                del self._shapes[index]
                self._redo_stack.append(entry)
                return entry.bounds()
            # Already removed by the eraser; nothing left to undo for it.
        return QRect()

    def redo(self) -> QRect:
        if not self._redo_stack:
            return QRect()
        entry = self._redo_stack.pop()
        self._history.append(entry)
        if isinstance(entry, _ClearRecord):
            entry.shapes = list(self._shapes)
            self._shapes.clear()
            return self._bounds_of(entry.shapes)
        self._shapes.append(entry)
        return entry.bounds()

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
    def _bounds_of(shapes: Iterable[Shape]) -> QRect:
        dirty = QRect()
        for shape in shapes:
            dirty = dirty.united(shape.bounds())
        return dirty

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

    def can_undo(self) -> bool:
        live = {id(shape) for shape in self._shapes}
        return any(isinstance(entry, _ClearRecord) or id(entry) in live for entry in self._history)

    def _index_of(self, shape: Shape) -> int | None:
        # Identity, not dataclass equality: comparing whole point lists is
        # slow and two shapes are only "the same" if they are one object.
        for index in range(len(self._shapes) - 1, -1, -1):
            if self._shapes[index] is shape:
                return index
        return None

    def can_redo(self) -> bool:
        return bool(self._redo_stack)

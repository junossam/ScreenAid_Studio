from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import QRect

from drawing.shapes import Shape


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
        for shape in sorted(self._shapes, key=lambda item: item.z_index, reverse=True):
            if shape.bounds().contains(point):
                self._shapes.remove(shape)
                self._redo_stack.clear()
                return shape.bounds()
        return QRect()

    def shapes(self) -> Iterable[Shape]:
        return tuple(sorted(self._shapes, key=lambda shape: shape.z_index))

    def is_empty(self) -> bool:
        return not self._shapes

    def can_redo(self) -> bool:
        return bool(self._redo_stack)

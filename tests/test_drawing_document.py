from __future__ import annotations

import unittest

from PySide6.QtCore import QPoint

from drawing.document import DrawingDocument
from drawing.shapes import Shape, ShapeType


class DrawingDocumentTests(unittest.TestCase):
    def test_add_and_clear_shape(self) -> None:
        document = DrawingDocument()
        shape = Shape(ShapeType.FREEHAND, [QPoint(0, 0), QPoint(10, 10)], "#fff", 3)

        dirty = document.add_shape(shape)

        self.assertFalse(dirty.isNull())
        self.assertEqual(len(tuple(document.shapes())), 1)
        self.assertFalse(document.clear().isNull())
        self.assertTrue(document.is_empty())

    def test_undo_and_redo_shape(self) -> None:
        document = DrawingDocument()
        shape = Shape(ShapeType.LINE, [QPoint(0, 0), QPoint(10, 10)], "#fff", 3)

        document.add_shape(shape)
        dirty = document.undo()

        self.assertFalse(dirty.isNull())
        self.assertTrue(document.is_empty())

        dirty = document.redo()

        self.assertFalse(dirty.isNull())
        self.assertEqual(len(tuple(document.shapes())), 1)

    def test_erase_at_removes_topmost_shape(self) -> None:
        document = DrawingDocument()
        bottom = Shape(ShapeType.RECTANGLE, [QPoint(0, 0), QPoint(20, 20)], "#fff", 3)
        top = Shape(ShapeType.RECTANGLE, [QPoint(0, 0), QPoint(20, 20)], "#fff", 3)
        document.add_shape(bottom)
        document.add_shape(top)

        dirty = document.erase_at(QPoint(10, 10))

        self.assertFalse(dirty.isNull())
        self.assertEqual(tuple(document.shapes()), (bottom,))

    def test_erase_at_does_not_hit_empty_corner_of_diagonal_line_bounds(self) -> None:
        document = DrawingDocument()
        line = Shape(ShapeType.LINE, [QPoint(0, 0), QPoint(100, 100)], "#fff", 3)
        document.add_shape(line)

        near_corner = document.erase_at(QPoint(95, 5))
        self.assertTrue(near_corner.isNull())
        self.assertEqual(len(tuple(document.shapes())), 1)

        on_the_line = document.erase_at(QPoint(50, 50))
        self.assertFalse(on_the_line.isNull())
        self.assertTrue(document.is_empty())

    def test_can_redo_tracks_redo_stack(self) -> None:
        document = DrawingDocument()
        shape = Shape(ShapeType.LINE, [QPoint(0, 0), QPoint(20, 20)], "#fff", 2)

        document.add_shape(shape)
        self.assertFalse(document.can_redo())
        document.undo()
        self.assertTrue(document.can_redo())
        document.redo()
        self.assertFalse(document.can_redo())


if __name__ == "__main__":
    unittest.main()

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

    def test_clear_can_be_undone_and_redone(self) -> None:
        document = DrawingDocument()
        first = Shape(ShapeType.LINE, [QPoint(0, 0), QPoint(20, 20)], "#fff", 2)
        second = Shape(ShapeType.LINE, [QPoint(30, 30), QPoint(40, 40)], "#fff", 2)
        document.add_shape(first)
        document.add_shape(second)

        document.clear()
        self.assertTrue(document.is_empty())
        self.assertTrue(document.can_undo())

        dirty = document.undo()
        self.assertFalse(dirty.isNull())
        self.assertEqual(tuple(document.shapes()), (first, second))

        document.redo()
        self.assertTrue(document.is_empty())

        document.undo()
        document.undo()
        self.assertEqual(tuple(document.shapes()), (first,))

    def test_shape_drawn_after_clear_is_undone_before_the_clear(self) -> None:
        document = DrawingDocument()
        before = Shape(ShapeType.LINE, [QPoint(0, 0), QPoint(20, 20)], "#fff", 2)
        after = Shape(ShapeType.LINE, [QPoint(30, 30), QPoint(40, 40)], "#fff", 2)
        document.add_shape(before)
        document.clear()
        document.add_shape(after)

        document.undo()
        self.assertTrue(document.is_empty())
        document.undo()
        self.assertEqual(tuple(document.shapes()), (before,))

    def test_clearing_an_empty_document_adds_no_history(self) -> None:
        document = DrawingDocument()

        self.assertTrue(document.clear().isNull())
        self.assertFalse(document.can_undo())

    def test_undo_skips_shapes_removed_by_eraser(self) -> None:
        document = DrawingDocument()
        kept = Shape(ShapeType.RECTANGLE, [QPoint(100, 100), QPoint(120, 120)], "#fff", 3)
        erased = Shape(ShapeType.RECTANGLE, [QPoint(0, 0), QPoint(20, 20)], "#fff", 3)
        document.add_shape(kept)
        document.add_shape(erased)
        document.erase_at(QPoint(10, 10))

        document.undo()

        self.assertTrue(document.is_empty())
        self.assertFalse(document.can_undo())

    def test_reset_discards_history(self) -> None:
        document = DrawingDocument()
        document.add_shape(Shape(ShapeType.LINE, [QPoint(0, 0), QPoint(20, 20)], "#fff", 2))

        document.reset()

        self.assertTrue(document.is_empty())
        self.assertFalse(document.can_undo())
        self.assertTrue(document.undo().isNull())


if __name__ == "__main__":
    unittest.main()

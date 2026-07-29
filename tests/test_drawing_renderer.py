from __future__ import annotations

import unittest

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QImage, QPainter

from drawing.renderer import ShapeRenderer
from drawing.shapes import Shape, ShapeType


class ShapeRendererTests(unittest.TestCase):
    def test_pixel_eraser_clears_existing_pixels(self) -> None:
        image = QImage(80, 40, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        renderer = ShapeRenderer()
        renderer.paint_shape(
            painter,
            Shape(
                ShapeType.FREEHAND,
                [QPoint(5, 20), QPoint(75, 20)],
                "#ff0000",
                12,
            ),
        )
        renderer.paint_shape(
            painter,
            Shape(
                ShapeType.ERASER,
                [QPoint(40, 4), QPoint(40, 36)],
                "#000000",
                14,
            ),
        )
        painter.end()

        self.assertEqual(image.pixelColor(40, 20).alpha(), 0)
        self.assertGreater(image.pixelColor(15, 20).alpha(), 0)


if __name__ == "__main__":
    unittest.main()

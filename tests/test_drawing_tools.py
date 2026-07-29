from __future__ import annotations

import unittest

from PySide6.QtCore import QPoint

from config.settings import DrawingSettings, EraserSettings
from core.event_bus import EventBus
from drawing.controller import DrawingController
from drawing.events import PointerEvent
from drawing.shapes import ShapeType
from drawing.tools import FreehandTool, create_tool


class FreehandToolTests(unittest.TestCase):
    def _settings(self, default_tool: str = "freehand") -> DrawingSettings:
        return DrawingSettings(
            enabled=True,
            default_tool=default_tool,
            pass_through_on_start=True,
            show_click_effects_while_drawing=False,
            confirm_clear_all=False,
            undo_limit=100,
            color="#00a6ff",
            width=4,
            line_style="solid",
            opacity=255,
            smoothing=True,
            toolbar_button_size=28,
            toolbar_x=20,
            toolbar_y=80,
        )

    def test_skips_tiny_movements(self) -> None:
        tool = FreehandTool(self._settings(), min_point_distance=4)
        tool.pointer_down(PointerEvent(QPoint(0, 0), 1))
        tool.pointer_move(PointerEvent(QPoint(1, 1), 2))
        tool.pointer_move(PointerEvent(QPoint(10, 0), 3))
        shape = tool.pointer_up(PointerEvent(QPoint(20, 0), 4))

        self.assertIsNotNone(shape)
        self.assertEqual(len(shape.points), 3)

    def test_factory_creates_two_point_shape_tool(self) -> None:
        tool = create_tool(self._settings("rectangle"))

        tool.pointer_down(PointerEvent(QPoint(0, 0), 1))
        tool.pointer_move(PointerEvent(QPoint(20, 10), 2))
        shape = tool.pointer_up(PointerEvent(QPoint(30, 15), 3))

        self.assertIsNotNone(shape)
        self.assertEqual(shape.shape_type, ShapeType.RECTANGLE)
        self.assertEqual(shape.points[-1], QPoint(30, 15))

    def test_line_tool_snaps_with_shift(self) -> None:
        tool = create_tool(self._settings("line"))

        tool.pointer_down(PointerEvent(QPoint(0, 0), 1))
        shape = tool.pointer_up(PointerEvent(QPoint(30, 10), 2, shift=True))

        self.assertIsNotNone(shape)
        self.assertEqual(shape.points[-1], QPoint(30, 0))

    def test_tool_shape_keeps_current_style(self) -> None:
        tool = create_tool(self._settings("line"))

        tool.pointer_down(PointerEvent(QPoint(0, 0), 1))
        shape = tool.pointer_up(PointerEvent(QPoint(30, 10), 2))

        self.assertIsNotNone(shape)
        self.assertEqual(shape.stroke_color, "#00a6ff")
        self.assertEqual(shape.stroke_width, 4)
        self.assertEqual(shape.stroke_style, "solid")

    def test_highlighter_is_wide_translucent_solid_freehand(self) -> None:
        tool = create_tool(self._settings("highlighter"))

        tool.pointer_down(PointerEvent(QPoint(0, 0), 1))
        shape = tool.pointer_up(PointerEvent(QPoint(30, 10), 2))

        self.assertIsNotNone(shape)
        self.assertEqual(shape.shape_type, ShapeType.FREEHAND)
        self.assertGreaterEqual(shape.stroke_width, 14)
        self.assertLessEqual(shape.stroke_opacity, 90)
        self.assertEqual(shape.stroke_style, "solid")

    def test_factory_creates_pixel_eraser_shape(self) -> None:
        tool = create_tool(self._settings("eraser"))

        tool.pointer_down(PointerEvent(QPoint(0, 0), 1))
        shape = tool.pointer_up(PointerEvent(QPoint(30, 10), 2))

        self.assertIsNotNone(shape)
        self.assertEqual(shape.shape_type, ShapeType.ERASER)
        self.assertEqual(shape.stroke_width, 4)

    def test_stamp_tool_creates_named_stamp_shape(self) -> None:
        tool = create_tool(self._settings("stamp_heart"))

        tool.pointer_down(PointerEvent(QPoint(40, 40), 1))
        shape = tool.pointer_up(PointerEvent(QPoint(40, 40), 2))

        self.assertIsNotNone(shape)
        self.assertEqual(shape.shape_type, ShapeType.STAMP)
        self.assertEqual(shape.stamp_name, "heart")
        self.assertEqual(shape.fill_color, "#00a6ff")
        self.assertGreaterEqual(shape.bounds().width(), 28)

    def test_controller_selects_tool_from_event(self) -> None:
        bus = EventBus()
        controller = DrawingController(self._settings(), EraserSettings(mode="object", size=24), bus)
        controller.start()

        bus.publish("drawing.tool.select", tool="arrow")
        bus.publish("drawing.style.change", color="#ff3b30", width=8, line_style="dash")
        bus.publish("drawing.pointer.down", event=PointerEvent(QPoint(0, 0), 1))
        bus.publish("drawing.pointer.up", event=PointerEvent(QPoint(20, 10), 2))

        shape = tuple(controller.document.shapes())[-1]
        self.assertEqual(shape.shape_type, ShapeType.ARROW)
        self.assertEqual(shape.stroke_color, "#ff3b30")
        self.assertEqual(shape.stroke_width, 8)
        self.assertEqual(shape.stroke_style, "dash")
        controller.stop()

    def test_controller_selects_stamp_from_event(self) -> None:
        bus = EventBus()
        controller = DrawingController(self._settings(), EraserSettings(mode="object", size=24), bus)
        controller.start()

        bus.publish("drawing.tool.select", tool="stamp_star")
        bus.publish("drawing.pointer.down", event=PointerEvent(QPoint(30, 30), 1))
        bus.publish("drawing.pointer.up", event=PointerEvent(QPoint(30, 30), 2))

        shape = tuple(controller.document.shapes())[-1]
        self.assertEqual(shape.shape_type, ShapeType.STAMP)
        self.assertEqual(shape.stamp_name, "star")
        controller.stop()

    def test_controller_uses_pixel_eraser_mode(self) -> None:
        bus = EventBus()
        controller = DrawingController(
            self._settings("eraser"),
            EraserSettings(mode="pixel", size=18),
            bus,
        )
        controller.start()

        bus.publish("drawing.pointer.down", event=PointerEvent(QPoint(0, 0), 1))
        bus.publish("drawing.pointer.move", event=PointerEvent(QPoint(10, 0), 2))
        bus.publish("drawing.pointer.up", event=PointerEvent(QPoint(20, 0), 3))

        shape = tuple(controller.document.shapes())[-1]
        self.assertEqual(shape.shape_type, ShapeType.ERASER)
        self.assertEqual(shape.stroke_width, 18)
        controller.stop()


if __name__ == "__main__":
    unittest.main()

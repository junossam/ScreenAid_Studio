from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QImage, QKeyEvent
from PySide6.QtWidgets import QApplication

from config.settings import (
    DRAWING_SHORTCUT_DEFAULTS,
    DrawingSettings,
    DrawingShortcutSettings,
    EraserSettings,
    PinnedWindowSettings,
)
from drawing.events import PointerEvent
from drawing.shapes import Shape, ShapeType
from drawing.tools import create_tool
from pinned.window import PinnedWindow


_APP = QApplication.instance() or QApplication([])


def _drawing_settings() -> DrawingSettings:
    return DrawingSettings(
        enabled=True,
        default_tool="freehand",
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


def _key(vk: int, qt_key: Qt.Key, modifiers=Qt.KeyboardModifier.NoModifier) -> QKeyEvent:
    return QKeyEvent(QEvent.Type.KeyPress, qt_key, modifiers, 0, vk, 0, "")


class PinnedAnnotationShortcutTest(unittest.TestCase):
    def setUp(self) -> None:
        image = QImage(200, 100, QImage.Format.Format_ARGB32)
        image.fill(0)
        self.window = PinnedWindow(
            image,
            PinnedWindowSettings(enabled=True, default_zoom=1.0, min_zoom=0.25, max_zoom=4.0, click_through=False),
            _drawing_settings(),
            EraserSettings(mode="object", size=24),
            shortcut_settings=DrawingShortcutSettings(enabled=True, keys=dict(DRAWING_SHORTCUT_DEFAULTS)),
        )

    def tearDown(self) -> None:
        self.window.close()

    def _add_shape(self) -> None:
        self.window._document.add_shape(
            Shape(shape_type=ShapeType.LINE, points=[QPoint(0, 0), QPoint(10, 10)], stroke_color="#ff0000", stroke_width=4)
        )

    def test_keys_are_ignored_outside_annotation_mode(self) -> None:
        handled = self.window.handle_shortcut_key(_key(0x38, Qt.Key.Key_8))

        self.assertFalse(handled)
        self.assertEqual(self.window._current_tool, "freehand")

    def test_tool_color_and_width_keys_in_annotation_mode(self) -> None:
        self.window.set_annotation_mode(True)

        self.assertTrue(self.window.handle_shortcut_key(_key(0x35, Qt.Key.Key_5)))
        self.assertTrue(self.window.handle_shortcut_key(_key(0x52, Qt.Key.Key_R)))
        self.assertTrue(self.window.handle_shortcut_key(_key(0xDD, Qt.Key.Key_BracketRight)))

        self.assertEqual(self.window._current_tool, "rectangle")
        self.assertEqual(self.window._current_color, "#0a84ff")
        self.assertEqual(self.window._current_width, 8)

    def test_repeating_stamp_and_eraser_keys_cycles(self) -> None:
        self.window.set_annotation_mode(True)

        self.window.handle_shortcut_key(_key(0x37, Qt.Key.Key_7))
        self.assertEqual(self.window._current_tool, "stamp_star")
        self.window.handle_shortcut_key(_key(0x37, Qt.Key.Key_7))
        self.assertEqual(self.window._current_tool, "stamp_heart")

        self.window.handle_shortcut_key(_key(0x38, Qt.Key.Key_8))
        self.assertEqual(self.window._current_tool, "eraser")
        self.assertEqual(self.window._eraser_settings.mode, "object")
        self.window.handle_shortcut_key(_key(0x38, Qt.Key.Key_8))
        self.assertEqual(self.window._eraser_settings.mode, "pixel")
        self.window.handle_shortcut_key(_key(0x37, Qt.Key.Key_7))
        self.assertEqual(self.window._current_tool, "stamp_star")

    def test_undo_redo_need_ctrl(self) -> None:
        self._add_shape()
        self.window.set_annotation_mode(True)

        self.assertFalse(self.window.handle_shortcut_key(_key(0x5A, Qt.Key.Key_Z)))
        self.assertTrue(
            self.window.handle_shortcut_key(_key(0x5A, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier))
        )
        self.assertTrue(self.window._document.is_empty())
        self.assertTrue(
            self.window.handle_shortcut_key(_key(0x59, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier))
        )
        self.assertFalse(self.window._document.is_empty())

    def test_disabled_shortcuts_do_nothing(self) -> None:
        self.window.set_shortcut_settings(DrawingShortcutSettings(enabled=False, keys=dict(DRAWING_SHORTCUT_DEFAULTS)))
        self.window.set_annotation_mode(True)

        self.assertFalse(self.window.handle_shortcut_key(_key(0x38, Qt.Key.Key_8)))

    def test_escape_cancels_stroke_then_leaves_annotation_mode(self) -> None:
        self.window.set_annotation_mode(True)
        self.window.handle_shortcut_key(_key(0x33, Qt.Key.Key_3))
        self.window._tool = create_tool(self.window._active_drawing_settings())
        self.window._tool.pointer_down(PointerEvent(QPoint(1, 1), 1))

        self.window._escape_pressed()

        self.assertIsNone(self.window._tool)
        self.assertTrue(self.window._annotation_mode)

        self.window._escape_pressed()

        self.assertFalse(self.window._annotation_mode)


if __name__ == "__main__":
    unittest.main()

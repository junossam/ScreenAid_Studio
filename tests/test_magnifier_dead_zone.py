from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from config.settings import DrawingSettings, EraserSettings, MagnifierSettings
from core.event_bus import EventBus
from magnifier.window import FullscreenMagnifierWindow


_APP = QApplication.instance() or QApplication([])


def _drawing_settings() -> DrawingSettings:
    return DrawingSettings(
        enabled=True,
        default_tool="pen",
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


class FullscreenMagnifierDeadZoneTests(unittest.TestCase):
    """1920x1080 monitor at 2x zoom with a dead zone of half the monitor, so
    the box spans x 480..1440 / y 270..810 in on-screen coordinates."""

    def setUp(self) -> None:
        settings = MagnifierSettings(enabled=True, scale=2.0, size=260, keep_drawings_on_close=False, dead_zone_scale=0.5)
        self.window = FullscreenMagnifierWindow(settings, _drawing_settings(), EraserSettings(mode="object", size=24), EventBus())
        self.window._screen_rect = QRect(0, 0, 1920, 1080)
        self.window._screen_image = QImage(1920, 1080, QImage.Format.Format_RGB32)
        self.window._active_scale = 2.0
        self.window._progress = 1.0
        self.window.resize(1920, 1080)
        self.window._center_on(QPoint(960, 540))

    def tearDown(self) -> None:
        self.window.deleteLater()

    def test_view_holds_still_while_cursor_stays_inside_the_dead_zone(self) -> None:
        self.window._pan_to_cursor(QPoint(1100, 600))
        self.assertEqual(self.window._anchor, QPoint(960, 540))
        self.assertEqual(self.window._cursor, QPoint(1100, 600))

    def test_view_pans_only_once_cursor_pushes_past_the_dead_zone(self) -> None:
        self.window._pan_to_cursor(QPoint(1300, 540))
        self.assertEqual(self.window._anchor, QPoint(1060, 540))

    def test_anchor_is_clamped_so_the_edge_of_the_screen_is_reachable(self) -> None:
        self.window._pan_to_cursor(QPoint(1919, 1079))
        self.assertEqual(self.window._anchor, QPoint(1440, 810))
        source = self.window._source_rect()
        self.assertAlmostEqual(source.right(), 1920)
        self.assertAlmostEqual(source.bottom(), 1080)

    def test_pointer_is_painted_without_errors(self) -> None:
        self.window._pan_to_cursor(QPoint(1100, 600))
        self.window.grab()


if __name__ == "__main__":
    unittest.main()

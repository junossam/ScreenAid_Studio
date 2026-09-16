from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

from capture.region_selection import RegionSelectionOverlay
from config.settings import RegionSelectionSettings
from core.event_bus import EventBus


_APP = QApplication.instance() or QApplication([])


def _settings() -> RegionSelectionSettings:
    return RegionSelectionSettings(
        dark_overlay_opacity=120,
        border_width=2,
        show_size=True,
        show_coordinates=True,
        minimum_width=4,
        minimum_height=4,
    )


class RegionSelectionFreezeBackgroundTests(unittest.TestCase):
    """Two monitors with different native resolution AND different DPI scale,
    side by side, mirroring a real mixed-DPI multi-monitor desktop:

    - Monitor A (primary, left): 3840x2160 physical @ 200% scale -> 1920x1080 logical.
    - Monitor B (secondary, right): 1920x1080 physical @ 100% scale -> 1920x1080 logical,
      placed immediately to the right of A in both physical and logical space.
    """

    def setUp(self) -> None:
        self.monitor_a = SimpleNamespace(
            szDevice="\\\\.\\DISPLAY1",
            rcMonitor=SimpleNamespace(left=0, top=0, right=3840, bottom=2160),
        )
        self.monitor_b = SimpleNamespace(
            szDevice="\\\\.\\DISPLAY2",
            rcMonitor=SimpleNamespace(left=3840, top=0, right=5760, bottom=1080),
        )
        self.screen_a = SimpleNamespace(
            name=lambda: "\\\\.\\DISPLAY1",
            geometry=lambda: _rect(0, 0, 1920, 1080),
            devicePixelRatio=lambda: 2.0,
        )
        self.screen_b = SimpleNamespace(
            name=lambda: "\\\\.\\DISPLAY2",
            geometry=lambda: _rect(1920, 0, 1920, 1080),
            devicePixelRatio=lambda: 1.0,
        )

        # Frozen "virtual desktop" image: left 3840px (monitor A's physical
        # span) painted red, the rest (monitor B's physical span) blue.
        self.frozen_image = QImage(5760, 2160, QImage.Format.Format_RGB32)
        self.frozen_image.fill(QColor("red"))
        for x in range(3840, 5760):
            for y in range(0, 1080):
                self.frozen_image.setPixelColor(x, y, QColor("blue"))

        self.overlay = RegionSelectionOverlay(EventBus(), _settings(), lambda rect: None)
        self.overlay._frozen_image = self.frozen_image
        self.overlay._frozen_origin = _point(0, 0)

    def _apply_patches(self) -> None:
        patch("overlay.coordinates.QGuiApplication.screens", return_value=[self.screen_a, self.screen_b]).start()
        patch("overlay.coordinates.QGuiApplication.screenAt", side_effect=self._screen_at).start()
        patch(
            "overlay.coordinates.display_monitor_infos",
            return_value=[self.monitor_a, self.monitor_b],
        ).start()
        self.addCleanup(patch.stopall)

    def _screen_at(self, point):
        if self.screen_a.geometry().contains(point):
            return self.screen_a
        if self.screen_b.geometry().contains(point):
            return self.screen_b
        return None

    def test_each_monitor_gets_its_own_correctly_sized_crop(self) -> None:
        self._apply_patches()
        pixmap_a = self.overlay._background_pixmap_for_screen(self.screen_a)
        pixmap_b = self.overlay._background_pixmap_for_screen(self.screen_b)

        self.assertIsNotNone(pixmap_a)
        self.assertIsNotNone(pixmap_b)
        # Each pixmap must be scaled down/up to that monitor's own LOGICAL
        # size, even though the two monitors have different native
        # resolutions and different DPI scale factors.
        self.assertEqual(pixmap_a.size().width(), 1920)
        self.assertEqual(pixmap_a.size().height(), 1080)
        self.assertEqual(pixmap_b.size().width(), 1920)
        self.assertEqual(pixmap_b.size().height(), 1080)

    def test_each_monitor_shows_only_its_own_slice_of_the_frozen_image(self) -> None:
        self._apply_patches()
        pixmap_a = self.overlay._background_pixmap_for_screen(self.screen_a)
        pixmap_b = self.overlay._background_pixmap_for_screen(self.screen_b)

        image_a = pixmap_a.toImage()
        image_b = pixmap_b.toImage()
        # Monitor A's crop must be entirely red (it only ever sees pixels
        # from its own physical span of the frozen image), never blue
        # (monitor B's span) - and vice versa. This is what would leak
        # wrong pixels across monitors if the per-monitor physical rect
        # math didn't account for each monitor's own resolution/DPI scale.
        self.assertEqual(image_a.pixelColor(0, 0).name(), QColor("red").name())
        self.assertEqual(image_a.pixelColor(1919, 1079).name(), QColor("red").name())
        self.assertEqual(image_b.pixelColor(0, 0).name(), QColor("blue").name())
        self.assertEqual(image_b.pixelColor(1919, 1079).name(), QColor("blue").name())

    def test_missing_frozen_image_falls_back_to_no_background(self) -> None:
        self.overlay._frozen_image = None
        self._apply_patches()
        pixmap = self.overlay._background_pixmap_for_screen(self.screen_a)
        self.assertIsNone(pixmap)


def _rect(x: int, y: int, w: int, h: int):
    from PySide6.QtCore import QRect

    return QRect(x, y, w, h)


def _point(x: int, y: int):
    from PySide6.QtCore import QPoint

    return QPoint(x, y)


if __name__ == "__main__":
    unittest.main()

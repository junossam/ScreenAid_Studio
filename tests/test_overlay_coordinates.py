from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtCore import QPoint, QRect

from overlay.coordinates import ScreenCoordinateMapper


class OverlayCoordinateTests(unittest.TestCase):
    def test_physical_to_qt_point_falls_back_to_raw_coordinates_without_screen(self) -> None:
        mapper = ScreenCoordinateMapper()

        with (
            patch("overlay.coordinates.monitor_info_from_point", return_value=None),
            patch("overlay.coordinates.QGuiApplication.screens", return_value=[]),
        ):
            point = mapper.physical_to_qt_point(-1280, 720)

        self.assertEqual(point, QPoint(-1280, 720))

    def test_physical_to_qt_point_scales_to_qt_screen_geometry(self) -> None:
        mapper = ScreenCoordinateMapper()
        monitor = SimpleNamespace(
            szDevice="\\\\.\\DISPLAY1",
            rcMonitor=SimpleNamespace(left=0, top=0, right=1920, bottom=1080),
        )
        screen = SimpleNamespace(
            name=lambda: "\\\\.\\DISPLAY1",
            geometry=lambda: QRect(0, 0, 1536, 864),
            devicePixelRatio=lambda: 1.25,
        )

        with (
            patch("overlay.coordinates.monitor_info_from_point", return_value=monitor),
            patch("overlay.coordinates.QGuiApplication.screens", return_value=[screen]),
        ):
            point = mapper.physical_to_qt_point(960, 540)

        self.assertEqual(point, QPoint(768, 432))

    def test_qt_virtual_screen_rect_uses_qt_screen_geometries(self) -> None:
        mapper = ScreenCoordinateMapper()
        screens = [
            SimpleNamespace(geometry=lambda: QRect(0, 0, 1536, 864)),
            SimpleNamespace(geometry=lambda: QRect(1536, 0, 1280, 720)),
        ]

        with patch("overlay.coordinates.QGuiApplication.screens", return_value=screens):
            rect = mapper.qt_virtual_screen_rect()

        self.assertEqual(rect, QRect(0, 0, 2816, 864))

    def test_work_area_uses_qt_available_geometry(self) -> None:
        mapper = ScreenCoordinateMapper()
        screen = SimpleNamespace(availableGeometry=lambda: QRect(0, 0, 1536, 824))

        with patch("overlay.coordinates.QGuiApplication.screenAt", return_value=screen):
            rect = mapper.work_area_for_point(QPoint(100, 100))

        self.assertEqual(rect, QRect(0, 0, 1536, 824))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtCore import QPoint, QRect

from overlay.coordinates import ScreenCoordinateMapper


ROOT = Path(__file__).resolve().parents[1]


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

    def test_physical_to_qt_rect_scales_gdi_rect_for_qt_fallback(self) -> None:
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
            rect = mapper.physical_to_qt_rect(QRect(200, 100, 401, 201))

        self.assertEqual(rect, QRect(160, 80, 321, 161))

    def test_qt_to_physical_point_scales_to_monitor_coordinates(self) -> None:
        mapper = ScreenCoordinateMapper()
        monitor = SimpleNamespace(
            szDevice="\\\\.\\DISPLAY1",
            rcMonitor=SimpleNamespace(left=0, top=0, right=1920, bottom=1080),
        )
        screen = SimpleNamespace(
            name=lambda: "\\\\.\\DISPLAY1",
            geometry=lambda: QRect(0, 0, 1536, 864),
            availableGeometry=lambda: QRect(0, 0, 1536, 824),
            devicePixelRatio=lambda: 1.25,
        )

        with (
            patch("overlay.coordinates.display_monitor_infos", return_value=[monitor]),
            patch("overlay.coordinates.QGuiApplication.screenAt", return_value=screen),
        ):
            point = mapper.qt_to_physical_point(QPoint(768, 432))

        self.assertEqual(point, QPoint(960, 540))

    def test_qt_to_physical_point_raises_when_monitor_enumeration_fails(self) -> None:
        mapper = ScreenCoordinateMapper()
        screen = SimpleNamespace(
            name=lambda: "\\\\.\\DISPLAY1",
            geometry=lambda: QRect(0, 0, 1536, 864),
            availableGeometry=lambda: QRect(0, 0, 1536, 824),
            devicePixelRatio=lambda: 1.25,
        )

        with (
            patch("overlay.coordinates.display_monitor_infos", side_effect=OSError("EnumDisplayMonitors failed")),
            patch("overlay.coordinates.QGuiApplication.screenAt", return_value=screen),
        ):
            with self.assertRaisesRegex(OSError, "EnumDisplayMonitors failed"):
                mapper.qt_to_physical_point(QPoint(768, 432))

    def test_qt_to_physical_rect_scales_selection_for_gdi_capture(self) -> None:
        mapper = ScreenCoordinateMapper()
        monitor = SimpleNamespace(
            szDevice="\\\\.\\DISPLAY1",
            rcMonitor=SimpleNamespace(left=0, top=0, right=1920, bottom=1080),
        )
        screen = SimpleNamespace(
            name=lambda: "\\\\.\\DISPLAY1",
            geometry=lambda: QRect(0, 0, 1536, 864),
            availableGeometry=lambda: QRect(0, 0, 1536, 824),
            devicePixelRatio=lambda: 1.25,
        )

        with (
            patch("overlay.coordinates.display_monitor_infos", return_value=[monitor]),
            patch("overlay.coordinates.QGuiApplication.screenAt", return_value=screen),
        ):
            rect = mapper.qt_to_physical_rect(QRect(160, 80, 321, 161))

        self.assertEqual(rect, QRect(200, 100, 401, 201))

    def test_rect_conversion_uses_all_four_corners(self) -> None:
        source = (ROOT / "overlay" / "coordinates.py").read_text(encoding="utf-8")

        self.assertIn("rect.topRight()", source)
        self.assertIn("rect.bottomLeft()", source)
        self.assertIn("self.physical_to_qt_point(rect.right(), rect.top())", source)
        self.assertIn("self.physical_to_qt_point(rect.left(), rect.bottom())", source)
        self.assertIn("_bounding_rect", source)

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

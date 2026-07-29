from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from PySide6.QtCore import QPoint, QRect

from overlay.coordinates import ScreenCoordinateMapper


class OverlayCoordinateTests(unittest.TestCase):
    def test_physical_to_qt_point_keeps_overlay_physical_coordinates(self) -> None:
        mapper = ScreenCoordinateMapper()

        point = mapper.physical_to_qt_point(-1280, 720)

        self.assertEqual(point, QPoint(-1280, 720))

    def test_work_area_uses_windows_physical_monitor_rect(self) -> None:
        mapper = ScreenCoordinateMapper()
        monitor = SimpleNamespace(
            rcWork=SimpleNamespace(left=-1920, top=0, right=0, bottom=1140),
        )

        with patch("overlay.coordinates.monitor_info_from_point", return_value=monitor):
            rect = mapper.work_area_for_point(QPoint(-1200, 600))

        self.assertEqual(rect, QRect(-1920, 0, 1920, 1140))


if __name__ == "__main__":
    unittest.main()

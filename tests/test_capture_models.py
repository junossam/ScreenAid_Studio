from __future__ import annotations

import unittest

from PySide6.QtCore import QRect

from capture.models import CaptureRequest, CaptureType


class CaptureModelTests(unittest.TestCase):
    def test_capture_request_keeps_region_rect(self) -> None:
        request = CaptureRequest(CaptureType.REGION, QRect(10, 20, 30, 40))

        self.assertEqual(request.capture_type, CaptureType.REGION)
        self.assertEqual(request.rect.width(), 30)
        self.assertTrue(request.include_annotations)

    def test_capture_types_include_static_modes(self) -> None:
        self.assertEqual(CaptureType.CURRENT_MONITOR.value, "current_monitor")
        self.assertEqual(CaptureType.VIRTUAL_SCREEN.value, "virtual_screen")
        self.assertEqual(CaptureType.ACTIVE_WINDOW.value, "active_window")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest
from datetime import datetime
from pathlib import Path
from shutil import rmtree

from PySide6.QtCore import QRect
from PySide6.QtGui import QImage

from capture.models import CaptureResult, CaptureType
from capture.services import ImageSaveService
from config.settings import CaptureSettings

ROOT = Path(__file__).resolve().parents[1]


class ImageSaveServiceTests(unittest.TestCase):
    def _settings(self) -> CaptureSettings:
        return CaptureSettings(
            enabled=True,
            default_mode="region",
            include_annotations=True,
            include_click_effects=False,
            include_cursor=False,
            copy_to_clipboard=True,
            auto_save=False,
            open_pinned_window=False,
            image_format="PNG",
            jpeg_quality=90,
            save_directory="captures",
            filename_pattern="ScreenAidStudio_{date}_{time}",
            show_notification=True,
            remember_last_region=True,
        )

    def _result(self, captured_at: datetime) -> CaptureResult:
        image = QImage(4, 4, QImage.Format.Format_RGB32)
        image.fill(0xFF0000)
        return CaptureResult(
            capture_type=CaptureType.REGION,
            image=image,
            virtual_rect=QRect(0, 0, 4, 4),
            width=4,
            height=4,
            dpi_x=96,
            dpi_y=96,
            captured_at=captured_at,
        )

    def test_second_capture_in_the_same_second_does_not_overwrite_the_first(self) -> None:
        root = ROOT / "tests" / ".tmp_capture_services"
        if root.exists():
            rmtree(root)
        root.mkdir()
        try:
            service = ImageSaveService(self._settings(), root)
            same_second = datetime(2026, 1, 1, 12, 0, 0)

            first_path = service.save(self._result(same_second))
            second_path = service.save(self._result(same_second))

            self.assertNotEqual(first_path, second_path)
            self.assertTrue(first_path.exists())
            self.assertTrue(second_path.exists())
        finally:
            if root.exists():
                rmtree(root)


if __name__ == "__main__":
    unittest.main()

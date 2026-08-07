from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QGuiApplication, QImage

from config.settings import CaptureSettings
from capture.models import CaptureResult


class ClipboardService:
    def copy_image(self, image: QImage) -> bool:
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:
            return False
        clipboard.setImage(image)
        return True


class ImageSaveService:
    def __init__(self, settings: CaptureSettings, base_dir: Path) -> None:
        self.settings = settings
        self.base_dir = base_dir

    def save(self, result: CaptureResult) -> Path:
        directory = Path(self.settings.save_directory)
        if not directory.is_absolute():
            directory = self.base_dir / directory
        directory.mkdir(parents=True, exist_ok=True)
        path = self._unique_path(directory, self._filename(result), self.settings.image_format.lower())
        image_format = self.settings.image_format.upper()
        if image_format == "JPG":
            image_format = "JPEG"
        ok = result.image.save(str(path), image_format, self.settings.jpeg_quality)
        if not ok:
            raise OSError(f"Failed to save capture: {path}")
        return path

    @staticmethod
    def _unique_path(directory: Path, stem: str, extension: str) -> Path:
        # The filename pattern only has second precision, so two captures
        # within the same second would otherwise silently overwrite one
        # another; append a counter instead.
        path = directory / f"{stem}.{extension}"
        counter = 1
        while path.exists():
            path = directory / f"{stem}_{counter}.{extension}"
            counter += 1
        return path

    def _filename(self, result: CaptureResult) -> str:
        date = result.captured_at.strftime("%Y-%m-%d")
        time = result.captured_at.strftime("%H-%M-%S")
        name = self.settings.filename_pattern.format(
            date=date,
            time=time,
            type=result.capture_type.value,
        )
        return "".join("_" if char in '<>:"/\\|?*' else char for char in name)

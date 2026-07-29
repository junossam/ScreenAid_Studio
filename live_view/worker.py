from __future__ import annotations

from PySide6.QtCore import QObject, QRect, Signal, Slot
from PySide6.QtGui import QImage

from capture.gdi import GdiCaptureBackend
from capture.models import CaptureRequest, CaptureType


class LiveCaptureWorker(QObject):
    frame_ready = Signal(QImage)
    failed = Signal(str)
    finished = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.backend = GdiCaptureBackend()

    @Slot(QRect)
    def capture(self, rect: QRect) -> None:
        try:
            request = CaptureRequest(CaptureType.REGION, rect.normalized(), include_annotations=False)
            self.frame_ready.emit(self.backend.capture_region(request).image)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()

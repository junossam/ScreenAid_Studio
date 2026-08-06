from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QRunnable, QRect, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QCursor

from capture.gdi import GdiCaptureBackend
from capture.models import CaptureRequest, CaptureResult, CaptureType
from capture.region_selection import RegionSelectionOverlay
from capture.services import ClipboardService, ImageSaveService
from config.settings import Settings
from core.event_bus import Event, EventBus, Subscription
from core.service import Service
from monitor.manager import virtual_screen_qrect
from overlay.coordinates import ScreenCoordinateMapper
from utils.winapi import cursor_pos, foreground_window_rect, monitor_info_from_point


class _CaptureWorkerSignals(QObject):
    completed = Signal(object)
    failed = Signal(str)


class _CaptureWorker(QRunnable):
    def __init__(
        self,
        request: CaptureRequest,
        source_monitor_id: str | None,
        source_window_handle: int | None,
    ) -> None:
        super().__init__()
        self.setAutoDelete(False)
        self.request = request
        self.source_monitor_id = source_monitor_id
        self.source_window_handle = source_window_handle
        self.signals = _CaptureWorkerSignals()

    def run(self) -> None:
        try:
            result = GdiCaptureBackend().capture_region(self.request)
            result.source_monitor_id = self.source_monitor_id
            result.source_window_handle = self.source_window_handle
            self.signals.completed.emit(result)
        except Exception as exc:
            self.signals.failed.emit(str(exc))


class CaptureManager(Service):
    def __init__(self, settings: Settings, bus: EventBus, base_dir: Path) -> None:
        self.settings = settings
        self.bus = bus
        self.clipboard = ClipboardService()
        self.saver = ImageSaveService(settings.capture, base_dir)
        self._coordinates = ScreenCoordinateMapper()
        self._thread_pool = QThreadPool()
        self._thread_pool.setMaxThreadCount(1)
        self._capture_running = False
        self._current_worker: _CaptureWorker | None = None
        self._selection: RegionSelectionOverlay | None = None
        self._last_region: QRect | None = None
        self._last_result: CaptureResult | None = None
        self._subscriptions: list[Subscription] = []

    def start(self) -> None:
        if self._subscriptions:
            return
        self._subscriptions = [
            self.bus.subscribe("capture.region", self._start_region_capture),
            self.bus.subscribe("capture.last_region", self._capture_last_region),
            self.bus.subscribe("capture.save_last", self._save_last_capture),
            self.bus.subscribe("capture.current_monitor", self._capture_current_monitor),
            self.bus.subscribe("capture.virtual_screen", self._capture_virtual_screen),
            self.bus.subscribe("capture.active_window", self._capture_active_window),
        ]

    def stop(self) -> None:
        for subscription in self._subscriptions:
            self.bus.unsubscribe(subscription)
        self._subscriptions.clear()
        if self._selection:
            self._selection.close()
            self._selection = None
        self._thread_pool.waitForDone(1000)
        self._current_worker = None

    def _start_region_capture(self, _event: Event) -> None:
        if self._selection:
            self._selection.close()
        self._selection = RegionSelectionOverlay(
            self.settings.region_selection,
            self._region_selected,
        )
        self._selection.begin()

    def _capture_last_region(self, _event: Event) -> None:
        if self._last_region is None:
            self.bus.publish("capture.failed", error="No previous capture region")
            return
        if not virtual_screen_qrect().intersects(self._last_region):
            self.bus.publish("capture.failed", error="Previous capture region is outside the current virtual screen")
            return
        self._capture_rect(CaptureType.REGION, self._last_region)

    def _save_last_capture(self, _event: Event) -> None:
        if self._last_result is None or self._last_result.image.isNull():
            self.bus.publish("capture.failed", error="No captured image to save")
            return
        try:
            saved_path = self.saver.save(self._last_result)
            self.bus.publish(
                "capture.completed",
                result=self._last_result,
                copied=False,
                saved_path=saved_path,
            )
        except Exception as exc:
            self.bus.publish("capture.failed", error=str(exc))

    def _region_selected(self, rect: QRect | None) -> None:
        if self._selection:
            self._selection.deleteLater()
            self._selection = None
        if rect is None:
            return
        if self.settings.capture.remember_last_region:
            self._last_region = rect
        QTimer.singleShot(0, lambda: self._capture_rect(CaptureType.REGION, rect))

    def _capture_current_monitor(self, _event: Event) -> None:
        try:
            point = self._cursor_pos()
            monitor = monitor_info_from_point(point.x, point.y)
            if monitor is None:
                raise OSError("MonitorFromPoint failed")
            rect = QRect(
                monitor.rcMonitor.left,
                monitor.rcMonitor.top,
                monitor.rcMonitor.right - monitor.rcMonitor.left,
                monitor.rcMonitor.bottom - monitor.rcMonitor.top,
            )
            self._capture_rect(CaptureType.CURRENT_MONITOR, rect, source_monitor_id=monitor.szDevice)
        except Exception as exc:
            self.bus.publish("capture.failed", error=str(exc))

    def _cursor_pos(self):
        try:
            return cursor_pos()
        except OSError:
            physical_point = self._coordinates.qt_to_physical_point(QCursor.pos())

            class CursorPoint:
                x = physical_point.x()
                y = physical_point.y()

            return CursorPoint()

    def _capture_virtual_screen(self, _event: Event) -> None:
        self._capture_rect(CaptureType.VIRTUAL_SCREEN, virtual_screen_qrect())

    def _capture_active_window(self, _event: Event) -> None:
        try:
            hwnd, rect = foreground_window_rect()
            qrect = QRect(rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top)
            self._capture_rect(CaptureType.ACTIVE_WINDOW, qrect, source_window_handle=hwnd)
        except Exception as exc:
            self._capture_running = False
            self._current_worker = None
            self.bus.publish("capture.failed", error=str(exc))

    def _capture_rect(
        self,
        capture_type: CaptureType,
        rect: QRect,
        source_monitor_id: str | None = None,
        source_window_handle: int | None = None,
    ) -> None:
        try:
            if self._capture_running:
                self.bus.publish("capture.failed", error="Capture is already running")
                return
            rect = rect.normalized()
            if rect.isNull() or rect.width() <= 0 or rect.height() <= 0:
                raise ValueError(f"Invalid capture region: {rect}")
            request = CaptureRequest(
                capture_type=capture_type,
                rect=rect,
                include_annotations=self.settings.capture.include_annotations,
                include_cursor=self.settings.capture.include_cursor,
            )
            self._capture_running = True
            self.bus.publish("overlay.capture_visuals.suspended", source="capture_manager", suspended=True)
            QTimer.singleShot(50, lambda: self._start_capture_worker(request, source_monitor_id, source_window_handle))
        except Exception as exc:
            self._capture_running = False
            self._current_worker = None
            self.bus.publish("overlay.capture_visuals.suspended", source="capture_manager", suspended=False)
            self.bus.publish("capture.failed", error=str(exc))

    def _start_capture_worker(
        self,
        request: CaptureRequest,
        source_monitor_id: str | None = None,
        source_window_handle: int | None = None,
    ) -> None:
        try:
            worker = _CaptureWorker(request, source_monitor_id, source_window_handle)
            worker.signals.completed.connect(self._capture_completed, Qt.ConnectionType.QueuedConnection)
            worker.signals.failed.connect(self._capture_failed, Qt.ConnectionType.QueuedConnection)
            self._current_worker = worker
            self._thread_pool.start(worker)
        except Exception as exc:
            self._capture_running = False
            self._current_worker = None
            self.bus.publish("overlay.capture_visuals.suspended", source="capture_manager", suspended=False)
            self.bus.publish("capture.failed", error=str(exc))

    def _capture_completed(self, result: CaptureResult) -> None:
        self._capture_running = False
        self._current_worker = None
        self.bus.publish("overlay.capture_visuals.suspended", source="capture_manager", suspended=False)
        self._after_capture(result)

    def _capture_failed(self, error: str) -> None:
        self._capture_running = False
        self._current_worker = None
        self.bus.publish("overlay.capture_visuals.suspended", source="capture_manager", suspended=False)
        self.bus.publish("capture.failed", error=error)

    def _after_capture(self, result: CaptureResult) -> None:
        self._last_result = result
        saved_path = None
        copied = False
        if self.settings.capture.copy_to_clipboard:
            copied = self.clipboard.copy_image(result.image)
        if self.settings.capture.auto_save:
            saved_path = self.saver.save(result)
        self.bus.publish(
            "capture.completed",
            result=result,
            copied=copied,
            saved_path=saved_path,
        )

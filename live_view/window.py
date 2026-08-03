from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, QThread, QTimer, Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont, QImage, QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import QMenu, QWidget

from config.settings import LiveViewSettings
from core.event_bus import EventBus
from core.localization import tr
from live_view.worker import LiveCaptureWorker
from overlay.coordinates import ScreenCoordinateMapper
from utils.winapi import set_click_through


class LiveViewWindow(QWidget):
    _capture_requested = Signal(QRect)

    FPS_PRESETS = (1, 5, 10, 15, 30)

    def __init__(self, rect: QRect, settings: LiveViewSettings, bus: EventBus) -> None:
        super().__init__()
        self.source_rect = rect.normalized()
        self.settings = settings
        self.bus = bus
        self._coordinates = ScreenCoordinateMapper()
        self._display_rect = self._coordinates.physical_to_qt_rect(self.source_rect)
        self._fps = self._clamp_fps(settings.default_fps)
        self._zoom = 1.0
        self._click_through = False
        self._paused = False
        self._running = False
        self._drag_pos: QPoint | None = None
        self._latest_image = QImage()
        self._last_error: str | None = None
        self._capture_in_flight = False
        self._pending_capture = False
        self._worker_thread: QThread | None = None
        self._worker: LiveCaptureWorker | None = None
        self._timer = QTimer(self)
        self._timer.setInterval(self._interval_ms())
        self._timer.timeout.connect(self._capture_next)
        self._setup_window()
        self._escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._escape_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._escape_shortcut.activated.connect(self.close)

    def start(self) -> None:
        self._running = True
        self._paused = False
        self._ensure_worker()
        self._capture_next()
        self._timer.start()

    def stop(self) -> None:
        self._running = False
        self._timer.stop()
        self._pending_capture = False
        self._shutdown_worker()

    def closeEvent(self, event) -> None:
        self.stop()
        super().closeEvent(event)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)
        if self._latest_image.isNull():
            if self._last_error:
                painter.setPen(QColor("white"))
                painter.setFont(QFont("Segoe UI", 10))
                painter.drawText(
                    self.rect().adjusted(12, 12, -12, -12),
                    Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
                    f"Live capture failed:\n{self._last_error}",
                )
            return
        pixmap = QPixmap.fromImage(self._latest_image).scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter.drawPixmap((self.width() - pixmap.width()) // 2, (self.height() - pixmap.height()) // 2, pixmap)

    def mousePressEvent(self, event) -> None:
        self._activate_for_keyboard()
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:
        self._activate_for_keyboard()
        step = 1.1 if event.angleDelta().y() > 0 else 1 / 1.1
        self.set_zoom(self._zoom * step)
        event.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            event.accept()
            return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event) -> None:
        self._activate_for_keyboard()
        menu = QMenu(self)
        zoom_in = QAction(tr("live.zoom_in"), self)
        zoom_out = QAction(tr("live.zoom_out"), self)
        reset = QAction(tr("live.reset_zoom"), self)
        click_through = QAction(tr("live.click_through"), self)
        click_through.setCheckable(True)
        click_through.setChecked(self._click_through)
        pause = QAction(tr("live.resume") if self._paused else tr("live.pause"), self)
        pin_current = QAction(tr("live.pin_current_frame"), self)
        pin_current.setEnabled(not self._latest_image.isNull())
        close = QAction(tr("live.close"), self)
        zoom_in.triggered.connect(lambda: self.set_zoom(self._zoom * 1.25))
        zoom_out.triggered.connect(lambda: self.set_zoom(self._zoom / 1.25))
        reset.triggered.connect(lambda: self.set_zoom(1.0))
        click_through.triggered.connect(self.set_click_through)
        pause.triggered.connect(self.toggle_pause)
        pin_current.triggered.connect(self.pin_current_frame)
        close.triggered.connect(self.close)
        for action in (zoom_in, zoom_out, reset, click_through):
            menu.addAction(action)
        fps_menu = menu.addMenu(tr("live.fps_menu"))
        for fps in self.FPS_PRESETS:
            action = QAction(f"{fps} FPS", self)
            action.setCheckable(True)
            action.setChecked(fps == self._fps)
            action.setEnabled(self.settings.min_fps <= fps <= self.settings.max_fps)
            action.triggered.connect(lambda _checked=False, value=fps: self.set_fps(value))
            fps_menu.addAction(action)
        menu.addSeparator()
        for action in (pause, pin_current, close):
            menu.addAction(action)
        menu.exec(event.globalPos())

    def set_fps(self, fps: int) -> None:
        self._fps = self._clamp_fps(fps)
        self._timer.setInterval(self._interval_ms())
        self.setWindowTitle(tr("live.title", fps=self._fps))

    def set_zoom(self, zoom: float) -> None:
        self._zoom = min(4.0, max(0.25, zoom))
        self.resize(self._scaled_size())
        self.update()

    def set_click_through(self, enabled: bool) -> None:
        self._click_through = enabled
        self._apply_click_through()

    def toggle_pause(self) -> None:
        self.set_paused(not self._paused)

    def set_paused(self, paused: bool) -> None:
        self._paused = paused
        if paused:
            self._timer.stop()
            self._pending_capture = False
        else:
            self._running = True
            self._ensure_worker()
            self._capture_next()
            self._timer.start()

    def pin_current_frame(self) -> None:
        if self._latest_image.isNull():
            self.bus.publish("pin.failed", error="No live frame is available")
            return
        self.bus.publish("pin.image", image=self._latest_image.copy(), display_size=QSize(self.size()))

    def _setup_window(self) -> None:
        self.setWindowTitle(tr("live.title", fps=self._fps))
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.resize(self._scaled_size())
        self._apply_click_through()

    def _capture_next(self) -> None:
        if not self._running or self._paused:
            return
        if self._capture_in_flight:
            self._pending_capture = True
            return
        self._ensure_worker()
        self._capture_in_flight = True
        self._capture_requested.emit(QRect(self.source_rect))

    def _frame_ready(self, image: QImage) -> None:
        if not self._running:
            return
        self._latest_image = image
        self._last_error = None
        self.update()

    def _capture_failed(self, error: str) -> None:
        if not self._running:
            return
        self._last_error = error
        self.update()

    def _capture_finished(self) -> None:
        self._capture_in_flight = False
        if self._pending_capture and self._running and not self._paused:
            self._pending_capture = False
            self._capture_next()

    def _ensure_worker(self) -> None:
        if self._worker_thread is not None:
            return
        self._worker_thread = QThread(self)
        self._worker = LiveCaptureWorker()
        self._worker.moveToThread(self._worker_thread)
        self._capture_requested.connect(self._worker.capture, Qt.ConnectionType.QueuedConnection)
        self._worker.frame_ready.connect(self._frame_ready)
        self._worker.failed.connect(self._capture_failed)
        self._worker.finished.connect(self._capture_finished)
        self._worker_thread.finished.connect(self._worker.deleteLater)
        self._worker_thread.start()

    def _shutdown_worker(self) -> None:
        if self._worker_thread is None or self._worker is None:
            self._capture_in_flight = False
            return
        for signal, slot in (
            (self._capture_requested, self._worker.capture),
            (self._worker.frame_ready, self._frame_ready),
            (self._worker.failed, self._capture_failed),
            (self._worker.finished, self._capture_finished),
        ):
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError):
                pass
        self._worker_thread.quit()
        self._worker_thread.wait(1000)
        self._worker_thread.deleteLater()
        self._worker_thread = None
        self._worker = None
        self._capture_in_flight = False

    def _interval_ms(self) -> int:
        return round(1000 / self._fps)

    def _clamp_fps(self, fps: int) -> int:
        return min(self.settings.max_fps, max(self.settings.min_fps, fps))

    def _scaled_size(self) -> QSize:
        return QSize(
            max(80, round(self._display_rect.width() * self._zoom)),
            max(60, round(self._display_rect.height() * self._zoom)),
        )

    def _apply_click_through(self) -> None:
        if self.winId():
            set_click_through(int(self.winId()), self._click_through)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self._click_through)

    def _activate_for_keyboard(self) -> None:
        if self._click_through:
            return
        self.activateWindow()
        self.setFocus(Qt.FocusReason.MouseFocusReason)

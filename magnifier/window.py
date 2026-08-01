from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QRect, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QImage, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import QWidget

from config.settings import MagnifierSettings
from core.event_bus import Event, EventBus, Subscription
from core.service import Service


class FullscreenMagnifierWindow(QWidget):
    ANIMATION_MS = 260
    FRAME_MS = 16
    MIN_SCALE = 1.0
    MAX_SCALE = 5.0
    WHEEL_SCALE_STEP = 0.2

    def __init__(self, settings: MagnifierSettings) -> None:
        super().__init__()
        self.settings = settings
        self._screen_image = QImage()
        self._screen_rect = QRect()
        self._anchor = QPoint()
        self._progress = 0.0
        self._active_scale = self.MIN_SCALE
        self._closing = False
        self._elapsed_ms = 0
        self._timer = QTimer(self)
        self._timer.setInterval(self.FRAME_MS)
        self._timer.timeout.connect(self._tick)
        self._follow_timer = QTimer(self)
        self._follow_timer.setInterval(16)
        self._follow_timer.timeout.connect(self._follow_cursor)
        self._escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._escape_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._escape_shortcut.activated.connect(self.close_with_animation)
        self._setup_window()

    def open_at_cursor(self) -> None:
        cursor = QCursor.pos()
        screen = QGuiApplication.screenAt(cursor) or QGuiApplication.primaryScreen()
        if screen is None:
            return
        self._screen_rect = screen.geometry()
        self._anchor = cursor - self._screen_rect.topLeft()
        pixmap = screen.grabWindow(0)
        self._screen_image = pixmap.toImage()
        if self._screen_image.isNull():
            return
        self._closing = False
        self._elapsed_ms = 0
        self._progress = 0.0
        self._active_scale = self._clamp_scale(self.settings.scale)
        self.setGeometry(self._screen_rect)
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        self._timer.start()
        self._follow_timer.start()

    def close_with_animation(self) -> None:
        if self._closing:
            return
        self._closing = True
        self._elapsed_ms = 0
        self._timer.start()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        if self._screen_image.isNull():
            painter.fillRect(self.rect(), QColor("black"))
            return
        source = self._source_rect()
        painter.drawImage(QRectF(self.rect()), self._screen_image, source)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close_with_animation()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        self._set_anchor_from_global(event.globalPosition().toPoint())
        event.accept()

    def wheelEvent(self, event) -> None:
        if self._closing:
            event.accept()
            return
        self._set_anchor_from_global(event.globalPosition().toPoint())
        steps = event.angleDelta().y() / 120
        if steps:
            self._active_scale = self._clamp_scale(self._active_scale + steps * self.WHEEL_SCALE_STEP)
            self._progress = 1.0
            self.update()
        event.accept()

    def closeEvent(self, event) -> None:
        self._timer.stop()
        self._follow_timer.stop()
        super().closeEvent(event)

    def _setup_window(self) -> None:
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.BlankCursor)

    def _tick(self) -> None:
        self._elapsed_ms += self.FRAME_MS
        ratio = min(1.0, self._elapsed_ms / self.ANIMATION_MS)
        eased = QEasingCurve(QEasingCurve.Type.InOutCubic).valueForProgress(ratio)
        self._progress = 1.0 - eased if self._closing else eased
        self.update()
        if ratio >= 1.0:
            self._timer.stop()
            if self._closing:
                self.hide()
                self._screen_image = QImage()
                self._follow_timer.stop()

    def _follow_cursor(self) -> None:
        if not self.isVisible() or self._screen_image.isNull():
            return
        self._set_anchor_from_global(QCursor.pos())

    def _set_anchor_from_global(self, cursor: QPoint) -> None:
        if not self._screen_rect.contains(cursor):
            return
        anchor = cursor - self._screen_rect.topLeft()
        if anchor == self._anchor:
            return
        self._anchor = anchor
        self.update()

    def _source_rect(self) -> QRectF:
        target_scale = self._clamp_scale(self._active_scale)
        zoom = 1.0 + (target_scale - 1.0) * self._progress
        image_width = self._screen_image.width()
        image_height = self._screen_image.height()
        if image_width <= 0 or image_height <= 0:
            return QRectF()

        ratio_x = image_width / max(1, self._screen_rect.width())
        ratio_y = image_height / max(1, self._screen_rect.height())
        anchor_x = self._anchor.x() * ratio_x
        anchor_y = self._anchor.y() * ratio_y
        source_width = image_width / zoom
        source_height = image_height / zoom
        left = self._clamp(anchor_x - source_width / 2, 0, image_width - source_width)
        top = self._clamp(anchor_y - source_height / 2, 0, image_height - source_height)
        return QRectF(left, top, source_width, source_height)

    @staticmethod
    def _clamp(value: float, minimum: float, maximum: float) -> float:
        return min(max(value, minimum), max(minimum, maximum))

    @classmethod
    def _clamp_scale(cls, value: float) -> float:
        return cls._clamp(float(value), cls.MIN_SCALE, cls.MAX_SCALE)


class MagnifierWindow(Service):
    def __init__(self, settings: MagnifierSettings, bus: EventBus) -> None:
        self.settings = settings
        self.bus = bus
        self._window = FullscreenMagnifierWindow(settings)
        self._subscriptions: list[Subscription] = []

    def start(self) -> None:
        if self._subscriptions:
            return
        self._subscriptions = [
            self.bus.subscribe("magnifier.fullscreen.toggle", self._toggle),
            self.bus.subscribe("settings.saved", self._settings_saved),
            self.bus.subscribe("app.pause.changed", self._pause_changed),
        ]

    def stop(self) -> None:
        for subscription in self._subscriptions:
            self.bus.unsubscribe(subscription)
        self._subscriptions.clear()
        self._window.close()

    def _toggle(self, _event: Event) -> None:
        if not self.settings.enabled:
            return
        if self._window.isVisible():
            self._window.close_with_animation()
            return
        self._window.open_at_cursor()

    def _settings_saved(self, event: Event) -> None:
        settings = event.payload.get("settings")
        if settings is not None:
            self.settings = settings.magnifier
            self._window.settings = self.settings

    def _pause_changed(self, event: Event) -> None:
        if bool(event.payload.get("paused", False)) and self._window.isVisible():
            self._window.close_with_animation()

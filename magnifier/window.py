from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QDateTime, QEasingCurve, QPoint, QPointF, QRect, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QImage, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import QWidget

from config.settings import DrawingSettings, MagnifierSettings
from core.event_bus import Event, EventBus, Subscription
from core.service import Service
from drawing.document import DrawingDocument
from drawing.events import PointerEvent
from drawing.renderer import ShapeRenderer
from drawing.shapes import Shape
from drawing.tools import DrawingTool, create_tool
from magnifier.windows_api import WindowsLiveMagnifier


class FullscreenMagnifierWindow(QWidget):
    ANIMATION_MS = 260
    FRAME_MS = 16
    MIN_SCALE = 1.0
    MAX_SCALE = 5.0
    WHEEL_SCALE_STEP = 0.2

    def __init__(self, settings: MagnifierSettings, drawing_settings: DrawingSettings, bus: EventBus) -> None:
        super().__init__()
        self.settings = settings
        self.drawing_settings = drawing_settings
        self.bus = bus
        self._screen_image = QImage()
        self._screen_rect = QRect()
        self._anchor = QPoint()
        self._progress = 0.0
        self._active_scale = self.MIN_SCALE
        self._closing = False
        self._drawing_active = False
        self._drawing = False
        self._drawing_cursor = QPointF()
        self._anchor_before_drawing = QPoint()
        self._ignore_follow_until_cursor_moves: QPoint | None = None
        self._elapsed_ms = 0
        self._document = DrawingDocument()
        self._tool: DrawingTool = create_tool(drawing_settings)
        self._renderer = ShapeRenderer()
        self._timer = QTimer(self)
        self._timer.setInterval(self.FRAME_MS)
        self._timer.timeout.connect(self._tick)
        self._follow_timer = QTimer(self)
        self._follow_timer.setInterval(16)
        self._follow_timer.timeout.connect(self._follow_cursor)
        self._escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._escape_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._escape_shortcut.activated.connect(self.close_with_animation)
        self._setup_window()

    def open_at_cursor(self) -> None:
        cursor = QCursor.pos()
        screen = QGuiApplication.screenAt(cursor) or QGuiApplication.primaryScreen()
        if screen is None:
            return
        self._screen_rect = screen.geometry()
        self._anchor = cursor - self._screen_rect.topLeft()
        self._apply_cursor()
        self._screen_image = self._grab_screen_image()
        if self._screen_image.isNull():
            return
        self._closing = False
        self._drawing = False
        self._tool.cancel()
        self._document.clear()
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
        for shape in self._document.shapes():
            self._paint_magnified_shape(painter, shape, source)
        preview = self._tool.preview()
        if preview:
            self._paint_magnified_shape(painter, preview, source)
        if self._drawing_active:
            self._paint_drawing_cursor(painter)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close_with_animation()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        if self._drawing_active and event.button() == Qt.MouseButton.LeftButton:
            self._drawing = True
            self._drawing_cursor = event.position()
            self._tool.pointer_down(self._pointer_event(event.position(), event))
            self._raise_drawing_toolbar()
            self.update()
            event.accept()
            return
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drawing:
            self._drawing_cursor = event.position()
            self._tool.pointer_move(self._pointer_event(event.position(), event))
            self._raise_drawing_toolbar()
            self.update()
            event.accept()
            return
        if self._drawing_active:
            self._drawing_cursor = event.position()
            self._raise_drawing_toolbar()
            self.update()
            event.accept()
            return
        self._set_anchor_from_global(event.globalPosition().toPoint())
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if self._drawing and event.button() == Qt.MouseButton.LeftButton:
            shape = self._tool.pointer_up(self._pointer_event(event.position(), event))
            self._drawing = False
            if shape is not None:
                self._document.add_shape(shape)
            self._raise_drawing_toolbar()
            self.update()
            event.accept()
            return
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
        self._finish_drawings()
        super().closeEvent(event)

    def _setup_window(self) -> None:
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._apply_cursor()

    def _tick(self) -> None:
        self._elapsed_ms += self.FRAME_MS
        ratio = min(1.0, self._elapsed_ms / self.ANIMATION_MS)
        eased = QEasingCurve(QEasingCurve.Type.InOutCubic).valueForProgress(ratio)
        self._progress = 1.0 - eased if self._closing else eased
        self.update()
        if ratio >= 1.0:
            self._timer.stop()
            if self._closing:
                self._finish_drawings()
                self.hide()
                self._screen_image = QImage()
                self._follow_timer.stop()

    def _follow_cursor(self) -> None:
        if not self.isVisible() or self._screen_image.isNull() or self._drawing_active:
            return
        cursor = QCursor.pos()
        if self._ignore_follow_until_cursor_moves is not None:
            if cursor == self._ignore_follow_until_cursor_moves:
                return
            self._ignore_follow_until_cursor_moves = None
        self._set_anchor_from_global(cursor)

    def _set_anchor_from_global(self, cursor: QPoint) -> None:
        if not self._screen_rect.contains(cursor):
            return
        anchor = cursor - self._screen_rect.topLeft()
        if anchor == self._anchor:
            return
        self._anchor = anchor
        self.update()

    def set_drawing_active(self, active: bool) -> None:
        self._drawing_active = active
        if active:
            self._anchor_before_drawing = QPoint(self._anchor)
            cursor = QCursor.pos() - self._screen_rect.topLeft()
            self._drawing_cursor = QPointF(cursor)
            self._raise_drawing_toolbar()
        if not active:
            self._drawing = False
            self._tool.cancel()
            self._anchor = QPoint(self._anchor_before_drawing)
            self._ignore_follow_until_cursor_moves = QCursor.pos()
        self._apply_cursor()
        self.update()

    def toggle_drawing_active(self) -> bool:
        self.set_drawing_active(not self._drawing_active)
        return self._drawing_active

    def is_drawing_active(self) -> bool:
        return self._drawing_active

    def set_drawing_settings(self, settings: DrawingSettings) -> None:
        self.drawing_settings = settings
        if not self._drawing:
            self._tool = create_tool(settings)

    def _grab_screen_image(self) -> QImage:
        screen = QGuiApplication.screenAt(self._screen_rect.center()) or QGuiApplication.primaryScreen()
        if screen is None:
            return QImage()
        return screen.grabWindow(0).toImage()

    def _pointer_event(self, point: QPointF, event) -> PointerEvent:
        modifiers = event.modifiers()
        return PointerEvent(
            position=self._window_to_screen_point(point),
            timestamp_ms=QDateTime.currentMSecsSinceEpoch(),
            shift=bool(modifiers & Qt.KeyboardModifier.ShiftModifier),
            alt=bool(modifiers & Qt.KeyboardModifier.AltModifier),
        )

    def _window_to_screen_point(self, point: QPointF) -> QPoint:
        source = self._source_rect()
        if source.isNull() or self._screen_image.isNull():
            return QPoint(round(point.x()), round(point.y())) + self._screen_rect.topLeft()
        image_x = source.left() + point.x() * source.width() / max(1, self.width())
        image_y = source.top() + point.y() * source.height() / max(1, self.height())
        screen_x = self._screen_rect.left() + image_x * self._screen_rect.width() / max(1, self._screen_image.width())
        screen_y = self._screen_rect.top() + image_y * self._screen_rect.height() / max(1, self._screen_image.height())
        return QPoint(round(screen_x), round(screen_y))

    def _paint_magnified_shape(self, painter: QPainter, shape: Shape, source: QRectF) -> None:
        transformed = self._shape_to_window(shape, source)
        if transformed is not None:
            self._renderer.paint_shape(painter, transformed)

    def _paint_drawing_cursor(self, painter: QPainter) -> None:
        painter.save()
        color = QColor(self.drawing_settings.color)
        color.setAlpha(230)
        outer = QColor("#ffffff")
        outer.setAlpha(230)
        point = self._drawing_cursor
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(outer)
        painter.drawEllipse(point, 6, 6)
        painter.setBrush(color)
        painter.drawEllipse(point, 3, 3)
        painter.restore()

    def _apply_cursor(self) -> None:
        if self._drawing_active:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.BlankCursor)

    def _raise_drawing_toolbar(self) -> None:
        self.bus.publish("drawing.toolbar.raise")

    def _shape_to_window(self, shape: Shape, source: QRectF) -> Shape | None:
        if self._screen_image.isNull() or source.isNull():
            return None
        ratio_x = self._screen_image.width() / max(1, self._screen_rect.width())
        ratio_y = self._screen_image.height() / max(1, self._screen_rect.height())
        scale_x = self.width() / max(1.0, source.width())
        scale_y = self.height() / max(1.0, source.height())
        points = []
        for point in shape.points:
            image_x = (point.x() - self._screen_rect.left()) * ratio_x
            image_y = (point.y() - self._screen_rect.top()) * ratio_y
            points.append(QPoint(round((image_x - source.left()) * scale_x), round((image_y - source.top()) * scale_y)))
        scale = max(0.2, (ratio_x * scale_x + ratio_y * scale_y) / 2)
        return replace(shape, points=points, stroke_width=max(1, round(shape.stroke_width * scale)))

    def _finish_drawings(self) -> None:
        was_drawing_active = self._drawing_active
        self._commit_preview_shape()
        if self.settings.keep_drawings_on_close:
            for shape in self._document.shapes():
                self.bus.publish("drawing.shape.commit", shape=shape)
            self.bus.publish("overlay.repaint")
        self._document.clear()
        self._tool.cancel()
        self._drawing = False
        self._drawing_active = False
        if was_drawing_active:
            self.bus.publish("drawing.mode.changed", pass_through=True, scope="magnifier")

    def _commit_preview_shape(self) -> None:
        preview = self._tool.preview()
        if preview is None:
            return
        self._document.add_shape(preview)
        self._tool.cancel()

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
    def __init__(self, settings: MagnifierSettings, drawing_settings: DrawingSettings, bus: EventBus) -> None:
        self.settings = settings
        self.bus = bus
        self._drawing_settings = drawing_settings
        self._window: FullscreenMagnifierWindow | None = None
        self._live_magnifier = WindowsLiveMagnifier(settings)
        self._live_magnifier.failed.connect(self._live_failed)
        self._subscriptions: list[Subscription] = []

    def start(self) -> None:
        if self._subscriptions:
            return
        if self._window is None:
            self._window = FullscreenMagnifierWindow(self.settings, self._drawing_settings, self.bus)
        self._subscriptions = [
            self.bus.subscribe("magnifier.fullscreen.toggle", self._toggle),
            self.bus.subscribe("magnifier.live.toggle", self._toggle_live),
            self.bus.subscribe("magnifier.close", self._close),
            self.bus.subscribe("magnifier.drawing.toggle", self._toggle_drawing),
            self.bus.subscribe("drawing.mode.changed", self._drawing_mode_changed),
            self.bus.subscribe("drawing.tool.changed", self._drawing_tool_changed),
            self.bus.subscribe("drawing.style.change", self._drawing_style_changed),
            self.bus.subscribe("settings.saved", self._settings_saved),
            self.bus.subscribe("app.pause.changed", self._pause_changed),
        ]

    def stop(self) -> None:
        for subscription in self._subscriptions:
            self.bus.unsubscribe(subscription)
        self._subscriptions.clear()
        self._live_magnifier.stop()
        if self._window is not None:
            self._window.close()

    def is_visible(self) -> bool:
        return self._window is not None and self._window.isVisible()

    def _toggle(self, _event: Event) -> None:
        if not self.settings.enabled:
            return
        if self._live_magnifier.is_active():
            self._live_magnifier.stop()
        if self._window is None:
            return
        if self._window.isVisible():
            self._window.close_with_animation()
            return
        self._window.open_at_cursor(live=False)

    def _toggle_live(self, _event: Event) -> None:
        if not self.settings.enabled:
            return
        if self._window is not None and self._window.isVisible():
            self._window.close_with_animation()
        self._live_magnifier.toggle()

    def _close(self, _event: Event) -> None:
        if self._live_magnifier.is_active():
            self._live_magnifier.stop()
        if self._window is not None and self._window.isVisible():
            self._window.close_with_animation()

    def _toggle_drawing(self, _event: Event) -> None:
        if self._window is None or not self._window.isVisible():
            return
        active = self._window.toggle_drawing_active()
        self.bus.publish("drawing.mode.changed", pass_through=not active, scope="magnifier")

    def _settings_saved(self, event: Event) -> None:
        settings = event.payload.get("settings")
        if settings is not None:
            self.settings = settings.magnifier
            self._drawing_settings = settings.drawing
            self._live_magnifier.update_settings(self.settings)
            if self._window is not None:
                self._window.settings = self.settings
                self._window.set_drawing_settings(settings.drawing)

    def _pause_changed(self, event: Event) -> None:
        if bool(event.payload.get("paused", False)) and self._live_magnifier.is_active():
            self._live_magnifier.stop()
        if self._window is not None and bool(event.payload.get("paused", False)) and self._window.isVisible():
            self._window.close_with_animation()

    def _drawing_mode_changed(self, event: Event) -> None:
        if self._window is not None:
            self._window.set_drawing_active(not bool(event.payload.get("pass_through", True)))

    def _drawing_tool_changed(self, event: Event) -> None:
        if self._window is None or self._drawing_settings is None:
            return
        tool = event.payload.get("tool")
        if isinstance(tool, str):
            self._drawing_settings = replace(self._drawing_settings, default_tool=tool)
            self._window.set_drawing_settings(self._drawing_settings)

    def _drawing_style_changed(self, event: Event) -> None:
        if self._window is None or self._drawing_settings is None:
            return
        color = event.payload.get("color", self._drawing_settings.color)
        width = event.payload.get("width", self._drawing_settings.width)
        line_style = event.payload.get("line_style", self._drawing_settings.line_style)
        if isinstance(color, str) and isinstance(width, int) and isinstance(line_style, str):
            self._drawing_settings = replace(self._drawing_settings, color=color, width=width, line_style=line_style)
            self._window.set_drawing_settings(self._drawing_settings)

    def _live_failed(self, error: str) -> None:
        self.bus.publish("live.failed", error=error)

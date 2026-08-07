from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QPoint, QRect, Qt
from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from config.settings import RegionSelectionSettings
from core.event_bus import Event, EventBus, Subscription
from mouse.events import MouseEvent, MouseEventType
from overlay.coordinates import ScreenCoordinateMapper


SelectionCallback = Callable[[QRect | None], None]


class RegionSelectionOverlay(QObject):
    """Lets the user drag-select a capture region across every monitor.

    One borderless topmost window is created per QScreen instead of a
    single window spanning the whole virtual desktop. A single HWND only
    has one DPI context, so a window stretched across monitors with
    different display scale factors renders and hit-tests incorrectly on
    every monitor except the one Windows picked for that context - clicks
    on the other monitors land offset from where the cursor visually is.
    Drag tracking uses the physical (unscaled) coordinates from the global
    mouse hook rather than each window's own Qt-local mouse events, so the
    result is correct regardless of which monitor(s) the drag crosses.
    """

    def __init__(self, bus: EventBus, settings: RegionSelectionSettings, on_done: SelectionCallback) -> None:
        super().__init__()
        self.bus = bus
        self.settings = settings
        self.on_done = on_done
        self._coordinates = ScreenCoordinateMapper()
        self._windows: list[_MonitorSelectionWindow] = []
        self._start: QPoint | None = None
        self._current: QPoint | None = None
        self._completed = False
        self._subscription: Subscription | None = None

    def begin(self) -> None:
        self._start = None
        self._current = None
        self._completed = False
        self._create_windows()
        self._subscription = self.bus.subscribe("mouse.event", self._handle_mouse_event)

    def close(self) -> None:
        self._teardown()

    def selection_rect_qt(self) -> QRect | None:
        if self._start is None or self._current is None:
            return None
        start = self._coordinates.physical_to_qt_point(self._start.x(), self._start.y())
        current = self._coordinates.physical_to_qt_point(self._current.x(), self._current.y())
        return QRect(start, current).normalized()

    def active_end_point_qt(self) -> QPoint | None:
        if self._current is None:
            return None
        return self._coordinates.physical_to_qt_point(self._current.x(), self._current.y())

    def cancel(self) -> None:
        self._finish(None)

    def _create_windows(self) -> None:
        self._destroy_windows()
        cursor = QCursor.pos()
        focus_screen = QGuiApplication.screenAt(cursor) or QGuiApplication.primaryScreen()
        focus_window: _MonitorSelectionWindow | None = None
        for screen in QGuiApplication.screens():
            window = _MonitorSelectionWindow(screen, self.settings, self)
            self._windows.append(window)
            window.show()
            if screen is focus_screen:
                focus_window = window
        if focus_window is not None:
            focus_window.raise_()
            focus_window.activateWindow()
            focus_window.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def _destroy_windows(self) -> None:
        for window in self._windows:
            window.close()
            window.deleteLater()
        self._windows.clear()

    def _handle_mouse_event(self, event: Event) -> None:
        mouse_event: MouseEvent = event.payload["event"]
        if mouse_event.event_type == MouseEventType.RIGHT_DOWN:
            self._finish(None)
            return
        if mouse_event.event_type == MouseEventType.LEFT_DOWN:
            self._start = QPoint(mouse_event.x, mouse_event.y)
            self._current = self._start
            self._repaint_all()
            return
        if mouse_event.event_type == MouseEventType.MOVE and self._start is not None:
            self._current = QPoint(mouse_event.x, mouse_event.y)
            self._repaint_all()
            return
        if mouse_event.event_type == MouseEventType.LEFT_UP and self._start is not None:
            self._current = QPoint(mouse_event.x, mouse_event.y)
            rect = QRect(self._start, self._current).normalized()
            if rect.width() < self.settings.minimum_width or rect.height() < self.settings.minimum_height:
                self._finish(None)
            else:
                self._finish(rect)

    def _repaint_all(self) -> None:
        for window in self._windows:
            window.update()

    def _finish(self, rect: QRect | None) -> None:
        if self._completed:
            return
        self._completed = True
        self._teardown()
        self.on_done(rect)

    def _teardown(self) -> None:
        if self._subscription is not None:
            self.bus.unsubscribe(self._subscription)
            self._subscription = None
        self._destroy_windows()


class _MonitorSelectionWindow(QWidget):
    def __init__(self, screen, settings: RegionSelectionSettings, coordinator: RegionSelectionOverlay) -> None:
        super().__init__()
        self.settings = settings
        self._coordinator = coordinator
        self._coordinates = ScreenCoordinateMapper()
        self._is_primary = screen is QGuiApplication.primaryScreen()
        self.setScreen(screen)
        self.setGeometry(screen.geometry())
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, self.settings.dark_overlay_opacity))
        selection = self._coordinator.selection_rect_qt()
        if selection is None:
            if self._is_primary:
                self._paint_hint(painter)
            return
        local = selection.translated(-self.geometry().topLeft())
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        painter.fillRect(local, QColor(0, 0, 0, 0))
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.setPen(QPen(QColor("#00a6ff"), self.settings.border_width))
        painter.drawRect(local.adjusted(0, 0, -1, -1))
        if self.settings.show_size and self._contains_qt_point(self._coordinator.active_end_point_qt()):
            self._paint_label(painter, local, selection)

    def mousePressEvent(self, event) -> None:
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        event.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._coordinator.cancel()
            event.accept()
            return
        super().keyPressEvent(event)

    def _contains_qt_point(self, point: QPoint | None) -> bool:
        if point is None:
            return False
        return self.geometry().contains(point)

    def _paint_label(self, painter: QPainter, local: QRect, selection_qt: QRect) -> None:
        physical_rect = self._coordinates.qt_to_physical_rect(selection_qt)
        text = f"{physical_rect.width()} x {physical_rect.height()}"
        if self.settings.show_coordinates:
            text = f"{text}  {physical_rect.left()}, {physical_rect.top()}"
        label_rect = QRect(local.left(), local.top() - 28, 160, 22)
        if label_rect.top() < 0:
            label_rect.moveTop(local.bottom() + 6)
        painter.fillRect(label_rect, QColor(0, 0, 0, 180))
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(label_rect.adjusted(6, 0, -6, 0), Qt.AlignmentFlag.AlignVCenter, text)

    def _paint_hint(self, painter: QPainter) -> None:
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(
            self.rect().adjusted(16, 16, -16, -16),
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
            "Drag to capture region. Esc or right-click to cancel.",
        )

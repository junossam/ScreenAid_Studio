from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from config.settings import RegionSelectionSettings
from overlay.coordinates import ScreenCoordinateMapper


SelectionCallback = Callable[[QRect | None], None]


class RegionSelectionOverlay(QWidget):
    def __init__(self, settings: RegionSelectionSettings, on_done: SelectionCallback) -> None:
        super().__init__()
        self.settings = settings
        self.on_done = on_done
        self._origin = QPoint(0, 0)
        self._start: QPoint | None = None
        self._current: QPoint | None = None
        self._completed = False
        self._coordinates = ScreenCoordinateMapper()
        self._setup_window()

    def begin(self) -> None:
        self._start = None
        self._current = None
        self._completed = False
        self._setup_window()
        self.show()
        self.raise_()
        self.activateWindow()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, self.settings.dark_overlay_opacity))
        selection = self._selection_rect_local()
        if not selection.isNull():
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(selection, QColor(0, 0, 0, 0))
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor("#00a6ff"), self.settings.border_width))
            painter.drawRect(selection.adjusted(0, 0, -1, -1))
            if self.settings.show_size:
                self._paint_label(painter, selection)
        else:
            painter.setPen(QColor("white"))
            painter.setFont(QFont("Segoe UI", 10))
            painter.drawText(
                self.rect().adjusted(16, 16, -16, -16),
                Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                "Drag to capture region. Esc or right-click to cancel.",
            )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self._finish(None)
            return
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore()
            return
        point = event.position().toPoint()
        self._start = point
        self._current = point
        self.update()
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._start is None:
            event.ignore()
            return
        old = self._selection_rect_local()
        self._current = event.position().toPoint()
        self.update(old.united(self._selection_rect_local()).adjusted(-80, -32, 80, 32))
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._start is None:
            event.ignore()
            return
        self._current = event.position().toPoint()
        selection = self._selection_rect_local()
        if (
            selection.width() < self.settings.minimum_width
            or selection.height() < self.settings.minimum_height
        ):
            self._finish(None)
            return
        rect = self._selection_rect_global()
        self._finish(rect)
        event.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._finish(None)
            event.accept()
            return
        super().keyPressEvent(event)

    def _setup_window(self) -> None:
        rect = self._virtual_screen_rect()
        self._origin = rect.topLeft()
        self.setGeometry(rect)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def _selection_rect_local(self) -> QRect:
        if self._start is None or self._current is None:
            return QRect()
        return QRect(self._start, self._current).normalized()

    def _selection_rect_global(self) -> QRect:
        qt_rect = self._selection_rect_local().translated(self._origin)
        return self._coordinates.qt_to_physical_rect(qt_rect)

    def _finish(self, rect: QRect | None) -> None:
        if self._completed:
            return
        self._completed = True
        self.hide()
        self.on_done(rect)

    def _paint_label(self, painter: QPainter, selection: QRect) -> None:
        physical_rect = self._coordinates.qt_to_physical_rect(selection.translated(self._origin))
        text = f"{physical_rect.width()} x {physical_rect.height()}"
        if self.settings.show_coordinates:
            text = f"{text}  {physical_rect.left()}, {physical_rect.top()}"
        label_rect = QRect(selection.left(), selection.top() - 28, 160, 22)
        if label_rect.top() < 0:
            label_rect.moveTop(selection.bottom() + 6)
        painter.fillRect(label_rect, QColor(0, 0, 0, 180))
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(label_rect.adjusted(6, 0, -6, 0), Qt.AlignmentFlag.AlignVCenter, text)

    def _virtual_screen_rect(self) -> QRect:
        return self._coordinates.qt_virtual_screen_rect()

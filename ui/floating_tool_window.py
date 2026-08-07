from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QLabel, QWidget

from core.localization import tr


class FloatingToolWindow(QWidget):
    input_geometry_changed = Signal(object)
    drag_finished = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._drag_pos: QPoint | None = None
        self._drag_moved = False
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def move_near(self, rect: QRect) -> None:
        self.adjustSize()
        screen = QGuiApplication.screenAt(rect.center()) or QGuiApplication.primaryScreen()
        bounds = screen.availableGeometry() if screen else QRect(0, 0, 1, 1)
        preferred = QPoint(rect.left() + max(0, (rect.width() - self.width()) // 2), rect.top() + 8)
        if rect.width() < self.width() or rect.height() < self.height() + 16:
            preferred = QPoint(rect.left(), rect.top() - self.height() - 8)
            if preferred.y() < bounds.top():
                preferred.setY(rect.bottom() + 8)
        self.move(self._clamp_point(preferred, bounds))

    def move_to_available(self, point: QPoint) -> None:
        self.adjustSize()
        screen = QGuiApplication.screenAt(point) or QGuiApplication.primaryScreen()
        bounds = screen.availableGeometry() if screen else QRect(0, 0, 1, 1)
        self.move(self._clamp_point(point, bounds))

    def ensure_inside_available(self) -> None:
        screen = QGuiApplication.screenAt(self.frameGeometry().center()) or QGuiApplication.primaryScreen()
        bounds = screen.availableGeometry() if screen else QRect(0, 0, 1, 1)
        self.move(self._clamp_point(self.frameGeometry().topLeft(), bounds))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._emit_input_geometry()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._emit_input_geometry()

    def moveEvent(self, event) -> None:
        super().moveEvent(event)
        self._emit_input_geometry()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._emit_input_geometry()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.begin_drag(event.globalPosition().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.drag_to(event.globalPosition().toPoint())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self.end_drag()
        super().mouseReleaseEvent(event)

    def begin_drag(self, global_pos: QPoint) -> None:
        self._drag_pos = global_pos - self.frameGeometry().topLeft()
        self._drag_moved = False

    def drag_to(self, global_pos: QPoint) -> None:
        if self._drag_pos is not None:
            self._drag_moved = True
            self.move(global_pos - self._drag_pos)

    def end_drag(self) -> None:
        moved = self._drag_moved
        self._drag_pos = None
        self._drag_moved = False
        if moved:
            self.drag_finished.emit(self)

    def _emit_input_geometry(self) -> None:
        self.input_geometry_changed.emit(self)

    def _clamp_point(self, point: QPoint, bounds: QRect) -> QPoint:
        return QPoint(
            min(max(point.x(), bounds.left()), max(bounds.left(), bounds.right() - self.width() + 1)),
            min(max(point.y(), bounds.top()), max(bounds.top(), bounds.bottom() - self.height() + 1)),
        )


class ToolDragHandle(QLabel):
    def __init__(self, owner: FloatingToolWindow) -> None:
        super().__init__(tr("tool.move"), owner)
        self._owner = owner
        self.setCursor(Qt.CursorShape.SizeAllCursor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._owner.begin_drag(event.globalPosition().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._owner.drag_to(event.globalPosition().toPoint())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._owner.end_drag()
        super().mouseReleaseEvent(event)

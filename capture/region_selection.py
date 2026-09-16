from __future__ import annotations

import ctypes
from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import QObject, QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from capture.gdi import GdiCaptureBackend
from capture.models import CaptureRequest, CaptureResult, CaptureType
from config.settings import RegionSelectionSettings
from core.event_bus import Event, EventBus, Subscription
from monitor.manager import virtual_screen_qrect
from mouse.events import MouseEvent, MouseEventType
from overlay.coordinates import ScreenCoordinateMapper
from utils.winapi import (
    HC_ACTION,
    KBDLLHOOKSTRUCT,
    LowLevelKeyboardProc,
    VK_ESCAPE,
    WH_KEYBOARD_LL,
    WM_KEYDOWN,
    WM_SYSKEYDOWN,
    user32,
)


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

    _escape_pressed = Signal()

    def __init__(
        self,
        bus: EventBus,
        settings: RegionSelectionSettings,
        on_done: SelectionCallback,
        freeze_background: bool = False,
    ) -> None:
        super().__init__()
        self.bus = bus
        self.settings = settings
        self.on_done = on_done
        self._freeze_background = freeze_background
        self._coordinates = ScreenCoordinateMapper()
        self._windows: list[_MonitorSelectionWindow] = []
        self._start: QPoint | None = None
        self._current: QPoint | None = None
        self._completed = False
        self._subscription: Subscription | None = None
        self._hook = None
        self._keyboard_proc = LowLevelKeyboardProc(self._keyboard_callback)
        self._escape_pressed.connect(self.cancel, Qt.ConnectionType.QueuedConnection)
        self._frozen_image: QImage | None = None
        self._frozen_origin = QPoint(0, 0)

    def begin(self) -> None:
        self._start = None
        self._current = None
        self._completed = False
        self._frozen_image = None
        self._frozen_origin = QPoint(0, 0)
        if self._freeze_background:
            # Snapshot the whole virtual desktop *before* any selection
            # window appears, then use that frozen bitmap (not a fresh
            # live grab) as both the drag preview and the final crop. A
            # fresh grab taken after the drag would already show whatever
            # popup the user is trying to capture as closed, because
            # starting the drag requires a real mouse-down click, and
            # Win32 popups (combobox/dropdown menus, Excel's AutoFilter,
            # ...) dismiss themselves on any outside click - regardless of
            # which window that click lands on. Freezing first sidesteps
            # this entirely: the pixels are already captured before that
            # dismissing click ever happens.
            self.bus.publish("overlay.capture_visuals.suspended", source="region_selection", suspended=True)
            QTimer.singleShot(50, self._begin_after_freeze)
        else:
            self._begin_now()

    def _begin_after_freeze(self) -> None:
        if self._completed:
            return
        self._capture_frozen_background()
        self.bus.publish("overlay.capture_visuals.suspended", source="region_selection", suspended=False)
        self._begin_now()

    def _begin_now(self) -> None:
        if self._completed:
            return
        self._create_windows()
        self._subscription = self.bus.subscribe("mouse.event", self._handle_mouse_event)
        self._install_hook()

    def _capture_frozen_background(self) -> None:
        try:
            virtual_rect = virtual_screen_qrect()
            request = CaptureRequest(CaptureType.REGION, virtual_rect, include_annotations=False)
            result = GdiCaptureBackend().capture_region(request)
        except Exception:
            self._frozen_image = None
            return
        self._frozen_image = result.image
        self._frozen_origin = virtual_rect.topLeft()

    def crop_frozen(self, rect: QRect) -> QImage | None:
        if self._frozen_image is None:
            return None
        local_rect = QRect(rect).translated(-self._frozen_origin).intersected(self._frozen_image.rect())
        if local_rect.isEmpty():
            return None
        return self._frozen_image.copy(local_rect)

    def frozen_capture_result(self, rect: QRect) -> CaptureResult | None:
        cropped = self.crop_frozen(rect)
        if cropped is None:
            return None
        return CaptureResult(
            capture_type=CaptureType.REGION,
            image=cropped,
            virtual_rect=rect,
            width=cropped.width(),
            height=cropped.height(),
            dpi_x=96,
            dpi_y=96,
            captured_at=datetime.now(),
            includes_annotations=False,
            includes_cursor=False,
        )

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
            background = self._background_pixmap_for_screen(screen)
            window = _MonitorSelectionWindow(screen, self.settings, self, background)
            self._windows.append(window)
            window.show()
            if screen is focus_screen:
                focus_window = window
        if focus_window is not None:
            # No activateWindow()/setFocus() here on purpose: stealing the
            # foreground activation would close whatever popup (combobox
            # dropdown, context menu, ...) the user is trying to capture,
            # since Win32 popups auto-dismiss when their owner loses
            # activation. The windows carry WindowDoesNotAcceptFocus
            # (WS_EX_NOACTIVATE) so showing/raising them can't activate them
            # either; Escape-to-cancel is handled via a low-level keyboard
            # hook instead of Qt focus-based key events.
            focus_window.raise_()

    def _background_pixmap_for_screen(self, screen) -> QPixmap | None:
        if self._frozen_image is None:
            return None
        physical_rect = self._coordinates.qt_to_physical_rect(QRect(screen.geometry()))
        source_rect = physical_rect.translated(-self._frozen_origin).intersected(self._frozen_image.rect())
        if source_rect.isEmpty():
            return None
        cropped = self._frozen_image.copy(source_rect)
        logical_size = screen.geometry().size()
        scaled = cropped.scaled(
            logical_size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        return QPixmap.fromImage(scaled)

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
        self._uninstall_hook()
        self._destroy_windows()

    def _install_hook(self) -> None:
        if self._hook:
            return
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._keyboard_proc, None, 0)

    def _uninstall_hook(self) -> None:
        if not self._hook:
            return
        user32.UnhookWindowsHookEx(self._hook)
        self._hook = None

    def _keyboard_callback(self, code: int, wparam: int, lparam: int) -> int:
        if code == HC_ACTION and wparam in {WM_KEYDOWN, WM_SYSKEYDOWN}:
            data = ctypes.cast(lparam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            if int(data.vkCode) == VK_ESCAPE:
                self._escape_pressed.emit()
                return 1
        return user32.CallNextHookEx(self._hook, code, wparam, lparam)


class _MonitorSelectionWindow(QWidget):
    def __init__(
        self,
        screen,
        settings: RegionSelectionSettings,
        coordinator: RegionSelectionOverlay,
        background: QPixmap | None = None,
    ) -> None:
        super().__init__()
        self.settings = settings
        self._coordinator = coordinator
        self._background_pixmap = background
        self._coordinates = ScreenCoordinateMapper()
        self._is_primary = screen is QGuiApplication.primaryScreen()
        self.setScreen(screen)
        self.setGeometry(screen.geometry())
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        # Never take keyboard focus / foreground activation (maps to
        # WS_EX_NOACTIVATE): showing/raising this window must not close
        # whatever popup the user is about to capture. See the comment in
        # RegionSelectionOverlay._create_windows.
        self.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        if self._background_pixmap is not None:
            painter.drawPixmap(0, 0, self._background_pixmap)
        painter.fillRect(self.rect(), QColor(0, 0, 0, self.settings.dark_overlay_opacity))
        selection = self._coordinator.selection_rect_qt()
        if selection is None:
            if self._is_primary:
                self._paint_hint(painter)
            return
        local = selection.translated(-self.geometry().topLeft())
        if self._background_pixmap is not None:
            # Reveal the crisp, un-dimmed frozen pixels inside the
            # selection instead of clearing to transparency - there is no
            # live desktop underneath to show through anymore.
            painter.drawPixmap(local, self._background_pixmap, local)
        else:
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

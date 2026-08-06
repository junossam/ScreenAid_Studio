from __future__ import annotations

import ctypes
from ctypes import wintypes

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QCursor, QGuiApplication

from config.settings import MagnifierSettings
from overlay.coordinates import ScreenCoordinateMapper
from utils.winapi import (
    RECT,
    VK_ESCAPE,
    cursor_pos,
    monitor_info_from_point,
    user32,
)


class WindowsMagnificationError(RuntimeError):
    pass


class _MagnificationApi:
    def __init__(self) -> None:
        self.dll = ctypes.WinDLL("Magnification.dll")
        self.dll.MagInitialize.argtypes = []
        self.dll.MagInitialize.restype = wintypes.BOOL
        self.dll.MagUninitialize.argtypes = []
        self.dll.MagUninitialize.restype = wintypes.BOOL
        self.dll.MagSetFullscreenTransform.argtypes = [ctypes.c_float, ctypes.c_int, ctypes.c_int]
        self.dll.MagSetFullscreenTransform.restype = wintypes.BOOL
        self.dll.MagSetInputTransform.argtypes = [
            wintypes.BOOL,
            ctypes.POINTER(RECT),
            ctypes.POINTER(RECT),
        ]
        self.dll.MagSetInputTransform.restype = wintypes.BOOL
        self.dll.MagShowSystemCursor.argtypes = [wintypes.BOOL]
        self.dll.MagShowSystemCursor.restype = wintypes.BOOL

    def initialize(self) -> None:
        if not self.dll.MagInitialize():
            raise WindowsMagnificationError("MagInitialize failed")

    def uninitialize(self) -> None:
        self.dll.MagUninitialize()

    def set_transform(self, scale: float, x_offset: int, y_offset: int) -> None:
        if not self.dll.MagSetFullscreenTransform(ctypes.c_float(scale), int(x_offset), int(y_offset)):
            raise WindowsMagnificationError("MagSetFullscreenTransform failed")

    def set_input_transform(self, enabled: bool, source: RECT, destination: RECT) -> bool:
        return bool(
            self.dll.MagSetInputTransform(
                wintypes.BOOL(enabled),
                ctypes.byref(source),
                ctypes.byref(destination),
            )
        )

    def show_cursor(self, visible: bool) -> None:
        self.dll.MagShowSystemCursor(wintypes.BOOL(visible))


class WindowsLiveMagnifier(QObject):
    failed = Signal(str)

    FOLLOW_MS = 16

    def __init__(self, settings: MagnifierSettings) -> None:
        super().__init__()
        self.settings = settings
        self._api: _MagnificationApi | None = None
        self._active = False
        self._input_transform_failed = False
        self._coordinates = ScreenCoordinateMapper()
        self._timer = QTimer(self)
        self._timer.setInterval(self.FOLLOW_MS)
        self._timer.timeout.connect(self._update_transform)

    def is_active(self) -> bool:
        return self._active

    def toggle(self) -> None:
        if self._active:
            self.stop()
        else:
            self.start()

    def start(self) -> None:
        if self._active:
            return
        try:
            self._api = _MagnificationApi()
            self._api.initialize()
            self._api.show_cursor(True)
            self._active = True
            self._input_transform_failed = False
            self._update_transform()
            self._timer.start()
        except Exception as exc:
            self._active = False
            self._timer.stop()
            if self._api is not None:
                self._api.uninitialize()
                self._api = None
            self.failed.emit(str(exc))

    def stop(self) -> None:
        if not self._active and self._api is None:
            return
        self._timer.stop()
        try:
            if self._api is not None:
                self._api.set_input_transform(False, RECT(), RECT())
                self._api.set_transform(1.0, 0, 0)
                self._api.show_cursor(True)
                self._api.uninitialize()
        finally:
            self._api = None
            self._active = False
            self._input_transform_failed = False

    def update_settings(self, settings: MagnifierSettings) -> None:
        self.settings = settings
        if self._active:
            self._update_transform()

    def poll_escape(self) -> None:
        if self._active and user32.GetAsyncKeyState(VK_ESCAPE) & 0x0001:
            self.stop()

    def _update_transform(self) -> None:
        if not self._active or self._api is None:
            return
        self.poll_escape()
        try:
            source, destination = self._rects_for_cursor()
            self._api.set_transform(self._scale(), source.left, source.top)
            if not self._api.set_input_transform(True, source, destination) and not self._input_transform_failed:
                self._input_transform_failed = True
                self.failed.emit("MagSetInputTransform failed. UIAccess privileges are required for mapped input.")
        except Exception as exc:
            self.failed.emit(str(exc))

    def _rects_for_cursor(self) -> tuple[RECT, RECT]:
        physical_cursor = self._cursor_physical_point()
        monitor = monitor_info_from_point(physical_cursor.x(), physical_cursor.y())
        if monitor is None:
            screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
            if screen is None:
                raise WindowsMagnificationError("No screen available")
            destination_qt = screen.geometry()
            top_left = self._coordinates.qt_to_physical_point(destination_qt.topLeft())
            bottom_right = self._coordinates.qt_to_physical_point(destination_qt.bottomRight())
            destination = RECT(top_left.x(), top_left.y(), bottom_right.x() + 1, bottom_right.y() + 1)
        else:
            destination = RECT(
                monitor.rcMonitor.left,
                monitor.rcMonitor.top,
                monitor.rcMonitor.right,
                monitor.rcMonitor.bottom,
            )

        scale = self._scale()
        source_width = max(1, round((destination.right - destination.left) / scale))
        source_height = max(1, round((destination.bottom - destination.top) / scale))
        left = self._clamp(
            physical_cursor.x() - source_width // 2,
            destination.left,
            destination.right - source_width,
        )
        top = self._clamp(
            physical_cursor.y() - source_height // 2,
            destination.top,
            destination.bottom - source_height,
        )
        source = RECT(left, top, left + source_width, top + source_height)
        return source, destination

    def _cursor_physical_point(self):
        try:
            point = cursor_pos()
            return self._Point(point.x, point.y)
        except Exception:
            point = self._coordinates.qt_to_physical_point(QCursor.pos())
            return self._Point(point.x(), point.y())

    def _scale(self) -> float:
        return max(1.1, min(5.0, float(self.settings.live_scale)))

    @staticmethod
    def _clamp(value: int, minimum: int, maximum: int) -> int:
        return min(max(value, minimum), max(minimum, maximum))

    class _Point:
        def __init__(self, x: int, y: int) -> None:
            self._x = int(x)
            self._y = int(y)

        def x(self) -> int:
            return self._x

        def y(self) -> int:
            return self._y

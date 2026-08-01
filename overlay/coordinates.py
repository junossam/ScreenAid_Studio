from __future__ import annotations

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QGuiApplication, QScreen

from monitor.manager import virtual_screen_qrect
from utils.winapi import monitor_info_from_point


class ScreenCoordinateMapper:
    def qt_virtual_screen_rect(self) -> QRect:
        screens = QGuiApplication.screens()
        if not screens:
            return virtual_screen_qrect()
        rect = screens[0].geometry()
        for screen in screens[1:]:
            rect = rect.united(screen.geometry())
        return rect

    def physical_to_qt_point(self, x: int, y: int) -> QPoint:
        monitor = monitor_info_from_point(x, y)
        screen = self._screen_for_monitor(monitor) if monitor is not None else None
        if monitor is None or screen is None:
            return QPoint(x, y)

        physical = monitor.rcMonitor
        physical_width = max(1, physical.right - physical.left)
        physical_height = max(1, physical.bottom - physical.top)
        geometry = screen.geometry()
        qt_x = geometry.left() + round((x - physical.left) * geometry.width() / physical_width)
        qt_y = geometry.top() + round((y - physical.top) * geometry.height() / physical_height)
        return QPoint(qt_x, qt_y)

    def work_area_for_point(self, point: QPoint) -> QRect:
        screen = QGuiApplication.screenAt(point)
        if screen is not None:
            return screen.availableGeometry()
        return self.qt_virtual_screen_rect()

    def _screen_for_monitor(self, monitor) -> QScreen | None:
        screens = QGuiApplication.screens()
        if not screens:
            return None

        device_name = str(getattr(monitor, "szDevice", "")).rstrip("\x00")
        if device_name:
            normalized_device = self._normalize_screen_name(device_name)
            for screen in screens:
                if self._normalize_screen_name(screen.name()) == normalized_device:
                    return screen

        physical = monitor.rcMonitor
        monitor_width = max(1, physical.right - physical.left)
        monitor_height = max(1, physical.bottom - physical.top)
        best_screen = None
        best_score = None
        for screen in screens:
            geometry = screen.geometry()
            scale_x = monitor_width / max(1, geometry.width())
            scale_y = monitor_height / max(1, geometry.height())
            score = abs(scale_x - scale_y) + abs(scale_x - screen.devicePixelRatio())
            if best_score is None or score < best_score:
                best_score = score
                best_screen = screen
        return best_screen

    @staticmethod
    def _normalize_screen_name(name: str) -> str:
        return name.replace("\\\\.\\", "").replace("\\", "").strip().lower()

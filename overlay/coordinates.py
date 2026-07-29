from __future__ import annotations

from PySide6.QtCore import QPoint, QRect

from monitor.manager import virtual_screen_qrect
from utils.winapi import monitor_info_from_point


class ScreenCoordinateMapper:
    def qt_virtual_screen_rect(self) -> QRect:
        return virtual_screen_qrect()

    def physical_to_qt_point(self, x: int, y: int) -> QPoint:
        return QPoint(x, y)

    def work_area_for_point(self, point: QPoint) -> QRect:
        monitor = monitor_info_from_point(point.x(), point.y())
        if monitor is None:
            return self.qt_virtual_screen_rect()
        work = monitor.rcWork
        return QRect(work.left, work.top, work.right - work.left, work.bottom - work.top)

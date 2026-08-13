from __future__ import annotations

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QGuiApplication, QScreen

from monitor.manager import virtual_screen_qrect, virtual_screen_rect
from utils.winapi import display_monitor_infos, monitor_info_from_point


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

    def physical_to_qt_rect(self, rect: QRect) -> QRect:
        rect = rect.normalized()
        return self._bounding_rect(
            (
                self.physical_to_qt_point(rect.left(), rect.top()),
                self.physical_to_qt_point(rect.right(), rect.top()),
                self.physical_to_qt_point(rect.left(), rect.bottom()),
                self.physical_to_qt_point(rect.right(), rect.bottom()),
            )
        )

    def qt_to_physical_point(self, point: QPoint) -> QPoint:
        screen = self._screen_for_qt_point(point)
        monitor = self._monitor_for_screen(screen) if screen is not None else None
        if screen is None or monitor is None:
            return QPoint(point)

        geometry = screen.geometry()
        physical = monitor.rcMonitor
        physical_width = max(1, physical.right - physical.left)
        physical_height = max(1, physical.bottom - physical.top)
        physical_x = physical.left + round((point.x() - geometry.left()) * physical_width / max(1, geometry.width()))
        physical_y = physical.top + round((point.y() - geometry.top()) * physical_height / max(1, geometry.height()))
        return QPoint(physical_x, physical_y)

    def qt_to_physical_rect(self, rect: QRect) -> QRect:
        rect = rect.normalized()
        return self._bounding_rect(
            (
                self.qt_to_physical_point(rect.topLeft()),
                self.qt_to_physical_point(rect.topRight()),
                self.qt_to_physical_point(rect.bottomLeft()),
                self.qt_to_physical_point(rect.bottomRight()),
            )
        )

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
        physical_virtual = virtual_screen_rect()
        physical_fraction = self._fraction_in_rect(
            (physical.left + physical.right) / 2,
            (physical.top + physical.bottom) / 2,
            physical_virtual.left,
            physical_virtual.top,
            physical_virtual.width,
            physical_virtual.height,
        )
        qt_virtual = self.qt_virtual_screen_rect()

        best_screen = None
        best_score = None
        for screen in screens:
            geometry = screen.geometry()
            center = geometry.center()
            qt_fraction = self._fraction_in_rect(
                center.x(), center.y(), qt_virtual.left(), qt_virtual.top(), qt_virtual.width(), qt_virtual.height()
            )
            score = abs(qt_fraction[0] - physical_fraction[0]) + abs(qt_fraction[1] - physical_fraction[1])
            if best_score is None or score < best_score:
                best_score = score
                best_screen = screen
        return best_screen

    def _monitor_for_screen(self, screen: QScreen | None):
        if screen is None:
            return None

        screen_name = self._normalize_screen_name(screen.name())
        monitors = display_monitor_infos()
        if screen_name:
            for monitor in monitors:
                if self._normalize_screen_name(str(getattr(monitor, "szDevice", "")).rstrip("\x00")) == screen_name:
                    return monitor

        geometry = screen.geometry()
        qt_virtual = self.qt_virtual_screen_rect()
        center = geometry.center()
        qt_fraction = self._fraction_in_rect(
            center.x(), center.y(), qt_virtual.left(), qt_virtual.top(), qt_virtual.width(), qt_virtual.height()
        )
        physical_virtual = virtual_screen_rect()

        best_monitor = None
        best_score = None
        for monitor in monitors:
            physical = monitor.rcMonitor
            physical_fraction = self._fraction_in_rect(
                (physical.left + physical.right) / 2,
                (physical.top + physical.bottom) / 2,
                physical_virtual.left,
                physical_virtual.top,
                physical_virtual.width,
                physical_virtual.height,
            )
            score = abs(qt_fraction[0] - physical_fraction[0]) + abs(qt_fraction[1] - physical_fraction[1])
            if best_score is None or score < best_score:
                best_score = score
                best_monitor = monitor
        return best_monitor

    def _screen_for_qt_point(self, point: QPoint) -> QScreen | None:
        screen = QGuiApplication.screenAt(point)
        if screen is not None:
            return screen
        screens = QGuiApplication.screens()
        if not screens:
            return None
        for candidate in screens:
            if candidate.geometry().contains(point):
                return candidate
        return min(
            screens,
            key=lambda candidate: (
                candidate.geometry().center().x() - point.x()
            )
            ** 2
            + (candidate.geometry().center().y() - point.y()) ** 2,
        )

    @staticmethod
    def _normalize_screen_name(name: str) -> str:
        return name.replace("\\\\.\\", "").replace("\\", "").strip().lower()

    @staticmethod
    def _fraction_in_rect(
        x: float, y: float, left: int, top: int, width: int, height: int
    ) -> tuple[float, float]:
        # Matches monitors by where they sit in the virtual desktop rather
        # than by scale factor - two monitors with identical resolution and
        # scaling score identically on scale alone, which used to make the
        # fallback (device-name matching failed) always pick the same
        # screen regardless of which monitor a point was actually on.
        fx = (x - left) / width if width else 0.0
        fy = (y - top) / height if height else 0.0
        return fx, fy

    @staticmethod
    def _bounding_rect(points: tuple[QPoint, QPoint, QPoint, QPoint]) -> QRect:
        xs = [point.x() for point in points]
        ys = [point.y() for point in points]
        return QRect(min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)

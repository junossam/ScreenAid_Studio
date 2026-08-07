from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, QTimer

from capture.gdi import GdiCaptureBackend
from capture.models import CaptureRequest, CaptureType
from capture.region_selection import RegionSelectionOverlay
from config.settings import Settings
from core.event_bus import Event, EventBus, Subscription
from core.service import Service
from overlay.coordinates import ScreenCoordinateMapper
from pinned.window import PinnedWindow


class PinnedWindowManager(Service):
    def __init__(self, settings: Settings, bus: EventBus) -> None:
        self.settings = settings
        self.bus = bus
        self.backend = GdiCaptureBackend()
        self._coordinates = ScreenCoordinateMapper()
        self._windows: list[PinnedWindow] = []
        self._selection: RegionSelectionOverlay | None = None
        self._last_result = None
        self._subscriptions: list[Subscription] = []

    def start(self) -> None:
        if self._subscriptions:
            return
        self._subscriptions = [
            self.bus.subscribe("capture.completed", self._capture_completed),
            self.bus.subscribe("pin.image", self._pin_image),
            self.bus.subscribe("pin.region", self._select_region),
            self.bus.subscribe("pin.last_capture", self._pin_last_capture),
            self.bus.subscribe("settings.saved", self._settings_saved),
        ]

    def stop(self) -> None:
        for subscription in self._subscriptions:
            self.bus.unsubscribe(subscription)
        self._subscriptions.clear()
        for window in tuple(self._windows):
            window.close()
        self._windows.clear()
        if self._selection:
            self._selection.close()
            self._selection = None
        self._last_result = None

    def _capture_completed(self, event: Event) -> None:
        self._last_result = event.payload["result"]
        if self.settings.capture.open_pinned_window:
            self._open_image(
                self._last_result.image,
                self._display_size_for_rect(self._last_result.virtual_rect),
                self._position_for_rect(self._last_result.virtual_rect),
            )

    def _pin_last_capture(self, _event: Event) -> None:
        if self._last_result is None:
            self.bus.publish("pin.failed", error="No capture result is available")
            return
        self._open_image(
            self._last_result.image,
            self._display_size_for_rect(self._last_result.virtual_rect),
            self._position_for_rect(self._last_result.virtual_rect),
        )

    def _pin_image(self, event: Event) -> None:
        image = event.payload.get("image")
        if image is None or image.isNull():
            self.bus.publish("pin.failed", error="No image is available")
            return
        display_size = event.payload.get("display_size")
        position = event.payload.get("position")
        self._open_image(
            image,
            display_size if isinstance(display_size, QSize) else None,
            position if isinstance(position, QPoint) else None,
        )

    def _select_region(self, _event: Event) -> None:
        if not self.settings.pinned_window.enabled:
            self.bus.publish("pin.failed", error="Pinned window is disabled")
            return
        if self._selection:
            self._selection.close()
        self._selection = RegionSelectionOverlay(self.bus, self.settings.region_selection, self._region_selected)
        self._selection.begin()

    def _region_selected(self, rect: QRect | None) -> None:
        if self._selection:
            self._selection.deleteLater()
            self._selection = None
        if rect is None or rect.normalized().isNull():
            return
        self.bus.publish("overlay.capture_visuals.suspended", source="pinned_capture", suspended=True)
        QTimer.singleShot(50, lambda: self._capture_selected_region(rect.normalized()))

    def _capture_selected_region(self, rect: QRect) -> None:
        try:
            request = CaptureRequest(CaptureType.REGION, rect, include_annotations=False)
            result = self.backend.capture_region(request)
        except Exception as exc:
            self.bus.publish("pin.failed", error=str(exc))
            return
        finally:
            self.bus.publish("overlay.capture_visuals.suspended", source="pinned_capture", suspended=False)
        self._last_result = result
        self._open_image(result.image, self._display_size_for_rect(result.virtual_rect), self._position_for_rect(result.virtual_rect))

    def _open_image(self, image, display_size: QSize | None = None, position: QPoint | None = None) -> None:
        if not self.settings.pinned_window.enabled:
            return
        window = PinnedWindow(
            image.copy(),
            self.settings.pinned_window,
            self.settings.drawing,
            self.settings.eraser,
            display_size=display_size,
            position=position,
        )
        window.destroyed.connect(lambda _obj=None, item=window: self._forget(item))
        self._windows.append(window)
        window.show()

    def _display_size_for_rect(self, rect: QRect) -> QSize:
        return self._coordinates.physical_to_qt_rect(rect).size()

    def _position_for_rect(self, rect: QRect) -> QPoint:
        return self._coordinates.physical_to_qt_rect(rect).topLeft()

    def _forget(self, window: PinnedWindow) -> None:
        if window in self._windows:
            self._windows.remove(window)

    def _settings_saved(self, event: Event) -> None:
        settings = event.payload.get("settings")
        if not isinstance(settings, Settings):
            return
        self.settings = settings
        for window in tuple(self._windows):
            window.set_toolbar_button_size(settings.drawing.toolbar_button_size)

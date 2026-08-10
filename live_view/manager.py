from __future__ import annotations

from PySide6.QtCore import QRect, QTimer

from capture.region_selection import RegionSelectionOverlay
from config.settings import Settings
from core.event_bus import Event, EventBus, Subscription
from core.service import Service
from live_view.window import LiveViewWindow


class LiveViewManager(Service):
    def __init__(self, settings: Settings, bus: EventBus) -> None:
        self.settings = settings
        self.bus = bus
        self._selection: RegionSelectionOverlay | None = None
        self._windows: list[LiveViewWindow] = []
        self._subscriptions: list[Subscription] = []
        self._globally_paused = False

    def start(self) -> None:
        if self._subscriptions:
            return
        self._subscriptions = [
            self.bus.subscribe("live.region", self._select_region),
            self.bus.subscribe("live.stop_all", self._stop_all),
            self.bus.subscribe("app.pause.changed", self._pause_all),
            self.bus.subscribe("settings.saved", self._settings_saved),
        ]

    def stop(self) -> None:
        for subscription in self._subscriptions:
            self.bus.unsubscribe(subscription)
        self._subscriptions.clear()
        self._stop_all(Event("live.stop_all", {}))
        if self._selection:
            self._selection.close()
            self._selection = None

    def _select_region(self, _event: Event) -> None:
        if not self.settings.live_view.enabled:
            self.bus.publish("live.failed", error="Live view is disabled")
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
        self.bus.publish("overlay.capture_visuals.suspended", source="live_view", suspended=True)
        window = LiveViewWindow(rect.normalized(), self.settings.live_view, self.bus, self.settings.window_border)
        window.destroyed.connect(lambda _obj=None, item=window: self._forget(item))
        self._windows.append(window)
        window.show()
        if self._globally_paused:
            window.set_paused(True)
        else:
            QTimer.singleShot(50, lambda: self._start_window(window))

    def _stop_all(self, _event: Event) -> None:
        for window in tuple(self._windows):
            window.stop()
            window.close()
        self._windows.clear()
        self.bus.publish("overlay.capture_visuals.suspended", source="live_view", suspended=False)

    def _forget(self, window: LiveViewWindow) -> None:
        if window in self._windows:
            self._windows.remove(window)
        if not self._windows:
            self.bus.publish("overlay.capture_visuals.suspended", source="live_view", suspended=False)

    def _start_window(self, window: LiveViewWindow) -> None:
        if window in self._windows and not self._globally_paused:
            window.start()

    def _pause_all(self, event: Event) -> None:
        self._globally_paused = bool(event.payload.get("paused", False))
        for window in tuple(self._windows):
            window.set_paused(self._globally_paused)

    def _settings_saved(self, event: Event) -> None:
        settings = event.payload.get("settings")
        if not isinstance(settings, Settings):
            return
        self.settings = settings
        for window in tuple(self._windows):
            window.set_border_settings(settings.window_border)

from __future__ import annotations

from PySide6.QtCore import QTimer

from core.event_bus import Event, EventBus, Subscription
from core.service import Service
from services.settings.settings_manager import SettingsManager


class ToolbarPositionStore(Service):
    def __init__(self, bus: EventBus, settings_manager: SettingsManager) -> None:
        self.bus = bus
        self.settings_manager = settings_manager
        self._subscription: Subscription | None = None
        self._pending: tuple[int, int] | None = None
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(700)
        self._timer.timeout.connect(self._flush)

    def start(self) -> None:
        if self._subscription is None:
            self._subscription = self.bus.subscribe("drawing_toolbar.position.changed", self._position_changed)

    def stop(self) -> None:
        if self._subscription is not None:
            self.bus.unsubscribe(self._subscription)
            self._subscription = None
        self._timer.stop()
        self._flush()

    def _position_changed(self, event: Event) -> None:
        x = event.payload.get("x")
        y = event.payload.get("y")
        if not isinstance(x, int) or not isinstance(y, int):
            return
        self._pending = (max(0, x), max(0, y))
        self._timer.start()

    def _flush(self) -> None:
        if self._pending is None:
            return
        x, y = self._pending
        self._pending = None
        try:
            parser = self.settings_manager.load_parser()
            if not parser.has_section("drawing"):
                parser.add_section("drawing")
            parser.set("drawing", "toolbar_x", str(x))
            parser.set("drawing", "toolbar_y", str(y))
            self.settings_manager.save_parser(parser)
        except Exception:
            pass

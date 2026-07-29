from __future__ import annotations

from pathlib import Path

from application.startup import StartupManager
from core.event_bus import Event, EventBus, Subscription
from core.service import Service
from services.settings.settings_manager import SettingsManager
from ui.settings_dialog import SettingsDialog


class SettingsWindowManager(Service):
    def __init__(
        self,
        bus: EventBus,
        settings_manager: SettingsManager,
        startup_manager: StartupManager,
        locales_dir: Path,
    ) -> None:
        self.bus = bus
        self.settings_manager = settings_manager
        self.startup_manager = startup_manager
        self.locales_dir = locales_dir
        self._dialog: SettingsDialog | None = None
        self._subscription: Subscription | None = None

    def start(self) -> None:
        if self._subscription is None:
            self._subscription = self.bus.subscribe("settings.open", self._open)

    def stop(self) -> None:
        if self._subscription is not None:
            self.bus.unsubscribe(self._subscription)
            self._subscription = None
        if self._dialog is not None:
            self._dialog.close()
            self._dialog = None

    def _open(self, _event: Event) -> None:
        if self._dialog is None:
            self._dialog = SettingsDialog(self.settings_manager, self.startup_manager, self.locales_dir, self.bus)
            self._dialog.finished.connect(lambda _result: self._clear_dialog())
        self._dialog.show()
        self._dialog.raise_()
        self._dialog.activateWindow()

    def _clear_dialog(self) -> None:
        self._dialog = None

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from application.commands import CommandId
from application.service_container import ServiceContainer
from config.settings import Settings
from core.localization import configure_localization
from services.settings.settings_manager import SettingsManager


class AppController:
    def __init__(self, settings: Settings, base_dir: Path, settings_manager: SettingsManager) -> None:
        self.settings = settings
        self.base_dir = base_dir
        configure_localization(base_dir / "locales", settings.app.language)
        self.container = ServiceContainer.build(
            settings=settings,
            base_dir=base_dir,
            settings_manager=settings_manager,
        )
        self.bus = self.container.event_bus
        self.dispatcher = self.container.command_dispatcher
        self.state_store = self.container.state_store
        self.bus.subscribe("manual.open", lambda _event: self._open_user_manual())
        self._wire_commands()

    def start(self) -> None:
        self.container.drawing.start()
        self.container.capture.start()
        self.container.pinned.start()
        self.container.live_view.start()
        self.container.settings_window.start()
        self.container.toolbar_position_store.start()
        self.container.drawing_toolbar.start()
        if self.settings.overlay.enabled:
            self.container.overlay.show()
            self.state_store.set_overlay_visible(True)
        self.container.tray.start()
        self.container.mouse.start()
        self.container.hotkeys.start()
        self.container.command_mode.start()
        self.state_store.set_running(True)

    def stop(self) -> None:
        self.container.command_mode.stop()
        self.container.hotkeys.stop()
        self.container.mouse.stop()
        self.container.drawing_toolbar.stop()
        self.container.toolbar_position_store.stop()
        self.container.settings_window.stop()
        self.container.live_view.stop()
        self.container.pinned.stop()
        self.container.capture.stop()
        self.container.tray.stop()
        self.container.overlay.close()
        self.state_store.set_running(False)
        QCoreApplication.quit()

    def _wire_commands(self) -> None:
        self.dispatcher.register(CommandId.QUIT_APPLICATION, self.stop)
        self.dispatcher.register(CommandId.TOGGLE_PAUSE, self._toggle_pause)
        self.dispatcher.register(CommandId.TOGGLE_OVERLAY, self._toggle_overlay)
        self.dispatcher.register(CommandId.TOGGLE_CLICK_EFFECTS, lambda: self.bus.publish("click_effects.toggle_temp"))
        self.dispatcher.register(CommandId.TOGGLE_DRAWING_MODE, self._toggle_drawing_mode)
        self.dispatcher.register(CommandId.DRAWING_PASS_THROUGH, self._drawing_pass_through)
        self.dispatcher.register(CommandId.CLEAR_DRAWING, self._clear_drawing)
        self.dispatcher.register(CommandId.UNDO_DRAWING, lambda: self.bus.publish("drawing.undo"))
        self.dispatcher.register(CommandId.REDO_DRAWING, lambda: self.bus.publish("drawing.redo"))
        self.dispatcher.register(CommandId.OPEN_SETTINGS, lambda: self.bus.publish("settings.open"))
        self.dispatcher.register(CommandId.OPEN_USER_MANUAL, self._open_user_manual)
        self.dispatcher.register(CommandId.OPEN_COMMAND_MODE, lambda: self.bus.publish("command_mode.open"))
        self.dispatcher.register(CommandId.CAPTURE_REGION, lambda: self._publish_when_active("capture.region"))
        self.dispatcher.register(CommandId.CAPTURE_LAST_REGION, lambda: self._publish_when_active("capture.last_region"))
        self.dispatcher.register(
            CommandId.CAPTURE_CURRENT_MONITOR,
            lambda: self._publish_when_active("capture.current_monitor"),
        )
        self.dispatcher.register(
            CommandId.CAPTURE_VIRTUAL_SCREEN,
            lambda: self._publish_when_active("capture.virtual_screen"),
        )
        self.dispatcher.register(
            CommandId.CAPTURE_ACTIVE_WINDOW,
            lambda: self._publish_when_active("capture.active_window"),
        )
        self.dispatcher.register(CommandId.PIN_REGION, lambda: self._publish_when_active("pin.region"))
        self.dispatcher.register(CommandId.PIN_LAST_CAPTURE, lambda: self._publish_when_active("pin.last_capture"))
        self.dispatcher.register(CommandId.LIVE_REGION, lambda: self._publish_when_active("live.region"))
        self.dispatcher.register(CommandId.LIVE_STOP_ALL, lambda: self.bus.publish("live.stop_all"))

    def _toggle_overlay(self) -> None:
        if self.container.overlay.isVisible():
            self.container.overlay.hide()
            self.state_store.set_overlay_visible(False)
        else:
            self.container.overlay.show()
            self.state_store.set_overlay_visible(True)

    def _toggle_drawing_mode(self) -> None:
        if self.state_store.state.is_paused:
            self._drawing_pass_through()
            self.bus.publish("app.command.blocked", reason="Application is paused")
            return
        self.bus.publish("drawing.mode.toggle")
        pass_through = not self.state_store.state.drawing_pass_through
        self.state_store.set_drawing_pass_through(pass_through)
        self.bus.publish("drawing.mode.changed", pass_through=pass_through)

    def _drawing_pass_through(self) -> None:
        self.bus.publish("drawing.mode.pass_through")
        self.state_store.set_drawing_pass_through(True)
        self.bus.publish("drawing.mode.changed", pass_through=True)

    def _clear_drawing(self) -> None:
        self.bus.publish("drawing.clear")
        self.bus.publish("overlay.clear")

    def _toggle_pause(self) -> None:
        paused = not self.state_store.state.is_paused
        self.state_store.set_paused(paused)
        if paused:
            self._drawing_pass_through()
            self.bus.publish("overlay.clear")
        self.bus.publish("app.pause.changed", paused=paused)

    def _publish_when_active(self, topic: str) -> None:
        if self.state_store.state.is_paused:
            self.bus.publish("app.command.blocked", reason="Application is paused")
            return
        self.bus.publish(topic)

    def _open_user_manual(self) -> None:
        manual_path = self.base_dir / "docs" / "user_manual.html"
        if not manual_path.exists():
            self.bus.publish("manual.failed", error=str(manual_path))
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(manual_path))):
            self.bus.publish("manual.failed", error=str(manual_path))

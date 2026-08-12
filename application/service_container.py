from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from application.command_dispatcher import CommandDispatcher
from application.startup import StartupManager
from application.state_store import ApplicationStateStore
from capture.manager import CaptureManager
from config.settings import Settings
from core.command_mode import CommandModeService
from core.event_bus import EventBus
from core.hotkeys import HotkeyManager
from drawing.controller import DrawingController
from live_view.manager import LiveViewManager
from live_zoom.service import LiveZoomService
from magnifier.window import MagnifierWindow
from mouse.hook import GlobalMouseHook
from overlay.window import OverlayWindow
from pinned.manager import PinnedWindowManager
from tray.tray_icon import TrayIcon
from ui.drawing_toolbar import DrawingToolbar
from ui.settings_manager import SettingsWindowManager
from ui.toolbar_position_store import ToolbarPositionStore
from services.settings.settings_manager import SettingsManager


@dataclass(slots=True)
class ServiceContainer:
    settings: Settings
    base_dir: Path
    event_bus: EventBus
    command_dispatcher: CommandDispatcher
    state_store: ApplicationStateStore
    overlay: OverlayWindow
    drawing: DrawingController
    capture: CaptureManager
    pinned: PinnedWindowManager
    live_view: LiveViewManager
    magnifier: MagnifierWindow
    live_zoom: LiveZoomService
    mouse: GlobalMouseHook
    hotkeys: HotkeyManager
    command_mode: CommandModeService
    tray: TrayIcon
    drawing_toolbar: DrawingToolbar
    toolbar_position_store: ToolbarPositionStore
    settings_window: SettingsWindowManager

    @classmethod
    def build(cls, settings: Settings, base_dir: Path, settings_manager: SettingsManager) -> "ServiceContainer":
        event_bus = EventBus()
        dispatcher = CommandDispatcher()
        state_store = ApplicationStateStore()
        overlay = OverlayWindow(settings=settings, bus=event_bus, base_dir=base_dir)
        drawing = DrawingController(settings=settings.drawing, eraser_settings=settings.eraser, bus=event_bus)
        capture = CaptureManager(settings=settings, bus=event_bus, base_dir=base_dir)
        pinned = PinnedWindowManager(settings=settings, bus=event_bus)
        live_view = LiveViewManager(settings=settings, bus=event_bus)
        magnifier = MagnifierWindow(
            settings=settings.magnifier,
            drawing_settings=settings.drawing,
            eraser_settings=settings.eraser,
            bus=event_bus,
        )
        live_zoom = LiveZoomService(settings=settings.live_zoom, bus=event_bus)
        mouse = GlobalMouseHook(bus=event_bus)
        hotkeys = HotkeyManager(dispatcher=dispatcher, hotkeys=settings.hotkeys, bus=event_bus)
        command_mode = CommandModeService(settings.command_mode, dispatcher=dispatcher, bus=event_bus)
        tray = TrayIcon(settings=settings, bus=event_bus, dispatcher=dispatcher, base_dir=base_dir)
        drawing_toolbar = DrawingToolbar(
            bus=event_bus,
            dispatcher=dispatcher,
            default_tool=settings.drawing.default_tool,
            default_color=settings.drawing.color,
            default_width=settings.drawing.width,
            default_line_style=settings.drawing.line_style,
            default_eraser_mode=settings.eraser.mode,
            toolbar_button_size=settings.drawing.toolbar_button_size,
            toolbar_x=settings.drawing.toolbar_x,
            toolbar_y=settings.drawing.toolbar_y,
        )
        toolbar_position_store = ToolbarPositionStore(bus=event_bus, settings_manager=settings_manager)
        startup = StartupManager(base_dir / "main.py")
        settings_window = SettingsWindowManager(
            bus=event_bus,
            settings_manager=settings_manager,
            startup_manager=startup,
            locales_dir=base_dir / "locales",
        )
        return cls(
            settings=settings,
            base_dir=base_dir,
            event_bus=event_bus,
            command_dispatcher=dispatcher,
            state_store=state_store,
            overlay=overlay,
            drawing=drawing,
            capture=capture,
            pinned=pinned,
            live_view=live_view,
            magnifier=magnifier,
            live_zoom=live_zoom,
            mouse=mouse,
            hotkeys=hotkeys,
            command_mode=command_mode,
            tray=tray,
            drawing_toolbar=drawing_toolbar,
            toolbar_position_store=toolbar_position_store,
            settings_window=settings_window,
        )

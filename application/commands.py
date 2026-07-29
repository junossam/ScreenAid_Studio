from __future__ import annotations

from enum import StrEnum


class CommandId(StrEnum):
    QUIT_APPLICATION = "app.quit"
    TOGGLE_PAUSE = "app.pause.toggle"
    TOGGLE_OVERLAY = "overlay.toggle"
    TOGGLE_CLICK_EFFECTS = "click_effects.toggle"
    TOGGLE_DRAWING_MODE = "drawing.mode.toggle"
    DRAWING_PASS_THROUGH = "drawing.mode.pass_through"
    CLEAR_DRAWING = "drawing.clear"
    UNDO_DRAWING = "drawing.undo"
    REDO_DRAWING = "drawing.redo"
    OPEN_SETTINGS = "settings.open"
    OPEN_USER_MANUAL = "manual.open"
    OPEN_COMMAND_MODE = "command_mode.open"
    CAPTURE_REGION = "capture.region"
    CAPTURE_LAST_REGION = "capture.last_region"
    CAPTURE_CURRENT_MONITOR = "capture.current_monitor"
    CAPTURE_VIRTUAL_SCREEN = "capture.virtual_screen"
    CAPTURE_ACTIVE_WINDOW = "capture.active_window"
    PIN_REGION = "pin.region"
    PIN_LAST_CAPTURE = "pin.last_capture"
    LIVE_REGION = "live.region"
    LIVE_STOP_ALL = "live.stop_all"

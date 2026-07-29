from __future__ import annotations

import unittest
from pathlib import Path

from application.state_store import ApplicationStateStore
from core.command_mode import parse_command_key
from core.hotkeys import MOD_ALT, MOD_CONTROL, VK_D, VK_E, VK_O, VK_SPACE, parse_hotkey


ROOT = Path(__file__).resolve().parents[1]


class GlobalPauseTest(unittest.TestCase):
    def _source(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_state_store_tracks_pause_state(self) -> None:
        store = ApplicationStateStore()
        self.assertFalse(store.state.is_paused)

        store.set_paused(True)

        self.assertTrue(store.state.is_paused)

    def test_pause_command_is_wired_to_controller_and_hotkey(self) -> None:
        commands = self._source("application/commands.py")
        controller = self._source("core/app_controller.py")
        hotkeys = self._source("core/hotkeys.py")

        self.assertIn('TOGGLE_PAUSE = "app.pause.toggle"', commands)
        self.assertIn("CommandId.TOGGLE_PAUSE, self._toggle_pause", controller)
        self.assertIn("app.pause.changed", controller)
        self.assertIn("app.command.blocked", controller)
        self.assertIn("HOTKEY_COMMAND_MODE", hotkeys)
        self.assertIn("HOTKEY_TOGGLE_CLICK_EFFECTS", hotkeys)
        self.assertIn("CommandId.OPEN_COMMAND_MODE", hotkeys)
        self.assertIn("CommandId.TOGGLE_CLICK_EFFECTS", hotkeys)
        self.assertNotIn("HOTKEY_TOGGLE_PAUSE", hotkeys)
        self.assertIn("settings.saved", hotkeys)
        self.assertIn("parse_hotkey", hotkeys)
        self.assertIn("OPEN_COMMAND_MODE", commands)
        self.assertIn('TOGGLE_CLICK_EFFECTS = "click_effects.toggle"', commands)
        self.assertIn("command_mode.open", controller)
        self.assertIn("click_effects.toggle_temp", controller)

    def test_hotkey_parser_accepts_config_text(self) -> None:
        self.assertEqual(parse_hotkey("Ctrl+Alt+D"), (MOD_CONTROL | MOD_ALT, VK_D))
        self.assertEqual(parse_hotkey("Ctrl+Alt+E"), (MOD_CONTROL | MOD_ALT, VK_E))
        self.assertEqual(parse_hotkey("Control + Alt + Space"), (MOD_CONTROL | MOD_ALT, VK_SPACE))
        self.assertIsNone(parse_hotkey(""))
        self.assertIsNone(parse_hotkey("Ctrl+Alt+Unknown"))

    def test_command_mode_parser_accepts_single_keys(self) -> None:
        self.assertEqual(parse_command_key("D"), VK_D)
        self.assertEqual(parse_command_key("O"), VK_O)
        self.assertEqual(parse_command_key("Space"), VK_SPACE)
        self.assertIsNone(parse_command_key(""))
        self.assertIsNone(parse_command_key("Ctrl+Alt+D"))

    def test_command_mode_service_is_wired(self) -> None:
        container = self._source("application/service_container.py")
        command_mode = self._source("core/command_mode.py")

        self.assertIn("CommandModeService", container)
        self.assertIn("settings.command_mode", container)
        self.assertIn("WH_KEYBOARD_LL", command_mode)
        self.assertIn("VK_ESCAPE", command_mode)
        self.assertIn("COMMAND_MODE_COMMANDS", command_mode)
        self.assertIn('"toggle_overlay": CommandId.TOGGLE_OVERLAY', command_mode)
        self.assertIn('"clear_drawing": CommandId.CLEAR_DRAWING', command_mode)
        self.assertIn('"pin_last_capture": CommandId.PIN_LAST_CAPTURE', command_mode)
        self.assertIn('"live_stop_all": CommandId.LIVE_STOP_ALL', command_mode)
        self.assertIn("COMMAND_MODE_GROUPS", command_mode)
        self.assertIn("command_mode.group.drawing", command_mode)
        self.assertIn("command_mode.group.capture", command_mode)
        self.assertNotIn("parts[:8]", command_mode)

    def test_pause_event_reaches_overlay_toolbar_live_and_tray(self) -> None:
        overlay = self._source("overlay/window.py")
        toolbar = self._source("ui/drawing_toolbar.py")
        live_manager = self._source("live_view/manager.py")
        tray = self._source("tray/tray_icon.py")

        self.assertIn('self.bus.subscribe("app.pause.changed", self._set_paused)', overlay)
        self.assertIn("if self._paused:", overlay)
        self.assertIn('self.bus.subscribe("app.pause.changed", self._pause_changed)', toolbar)
        self.assertIn('self.bus.subscribe("app.pause.changed", self._pause_all)', live_manager)
        self.assertIn("window.set_paused(self._globally_paused)", live_manager)
        self.assertIn('self._action(tr("tray.pause_all"), CommandId.TOGGLE_PAUSE)', tray)
        self.assertIn('tr("tray.resume_all")', tray)


if __name__ == "__main__":
    unittest.main()

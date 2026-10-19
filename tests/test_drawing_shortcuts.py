from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from application.command_dispatcher import CommandDispatcher
from application.commands import CommandId
from config.settings import DRAWING_SHORTCUT_DEFAULTS, DrawingShortcutSettings, Settings
from core.drawing_shortcuts import ESCAPE_ACTION, DrawingShortcutService, build_bindings
from core.event_bus import EventBus
from core.hotkeys import MOD_CONTROL, VK_D, VK_Q, VK_Y, VK_Z
from utils.winapi import VK_ESCAPE


class DrawingShortcutBindingTest(unittest.TestCase):
    def test_default_keys_all_parse_and_do_not_collide(self) -> None:
        bindings = build_bindings(DRAWING_SHORTCUT_DEFAULTS)
        bound = {name for name, text in DRAWING_SHORTCUT_DEFAULTS.items() if text.strip()}

        self.assertEqual(set(bindings.values()) - {ESCAPE_ACTION}, bound)
        self.assertEqual(bindings[(0, 0x31)], "tool_freehand")
        self.assertEqual(bindings[(0, 0x38)], "tool_eraser")
        self.assertEqual(bindings[(MOD_CONTROL, VK_Z)], "undo")
        self.assertEqual(bindings[(MOD_CONTROL, VK_Y)], "redo")
        self.assertEqual(bindings[(MOD_CONTROL, VK_D)], "clear")
        self.assertEqual(bindings[(0, VK_Q)], "color_1")
        self.assertEqual(bindings[(0, VK_Y)], "color_6")
        self.assertEqual(bindings[(0, 0xDB)], "width_down")
        self.assertEqual(bindings[(0, VK_ESCAPE)], ESCAPE_ACTION)

    def test_plain_key_does_not_match_modified_binding(self) -> None:
        bindings = build_bindings({"undo": "Ctrl+Z"})

        self.assertNotIn((0, VK_Z), bindings)

    def test_empty_and_invalid_keys_are_unbound(self) -> None:
        bindings = build_bindings({"clear": "", "undo": "Ctrl+?"})

        self.assertEqual(set(bindings.values()), {ESCAPE_ACTION})

    def test_settings_load_defaults_and_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.ini"
            path.write_text("[drawing_shortcuts]\nenabled = false\ntool_freehand = U\n", encoding="utf-8")

            settings = Settings.load(path)

        self.assertFalse(settings.drawing_shortcuts.enabled)
        self.assertEqual(settings.drawing_shortcuts.keys["tool_freehand"], "U")
        self.assertEqual(settings.drawing_shortcuts.keys["tool_eraser"], "8")


class DrawingShortcutActionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.bus = EventBus()
        self.dispatcher = CommandDispatcher()
        self.dispatched: list[str] = []
        for command in (CommandId.UNDO_DRAWING, CommandId.REDO_DRAWING, CommandId.DRAWING_PASS_THROUGH):
            self.dispatcher.register(command, lambda command=command: self.dispatched.append(command))
        self.published: list[tuple[str, dict]] = []
        for topic in ("drawing.tool.select", "drawing.toolbar.color.select", "drawing.toolbar.width.step"):
            self.bus.subscribe(topic, lambda event: self.published.append((event.name, dict(event.payload))))
        self.service = DrawingShortcutService(
            DrawingShortcutSettings(enabled=False, keys=dict(DRAWING_SHORTCUT_DEFAULTS)),
            dispatcher=self.dispatcher,
            bus=self.bus,
        )
        self.service.start()

    def tearDown(self) -> None:
        self.service.stop()

    def _enter_drawing_mode(self, scope: str = "overlay") -> None:
        self.bus.publish("drawing.mode.changed", pass_through=False, scope=scope)

    def test_actions_are_ignored_outside_drawing_mode(self) -> None:
        self.service._handle_action("tool_eraser")
        self.service._handle_action("undo")

        self.assertEqual(self.published, [])
        self.assertEqual(self.dispatched, [])

    def test_actions_map_to_events_and_commands(self) -> None:
        self._enter_drawing_mode()

        self.service._handle_action("tool_stamp")
        self.service._handle_action("color_4")
        self.service._handle_action("width_up")
        self.service._handle_action("undo")

        self.assertEqual(
            self.published,
            [
                ("drawing.tool.select", {"tool": "stamp_star"}),
                ("drawing.toolbar.color.select", {"index": 3}),
                ("drawing.toolbar.width.step", {"step": 1}),
            ],
        )
        self.assertEqual(self.dispatched, [CommandId.UNDO_DRAWING])

    def test_magnifier_drawing_scope_is_not_handled(self) -> None:
        self._enter_drawing_mode(scope="magnifier")

        self.service._handle_action("undo")

        self.assertEqual(self.dispatched, [])

    def test_pause_disables_actions(self) -> None:
        self._enter_drawing_mode()
        self.bus.publish("app.pause.changed", paused=True)

        self.service._handle_action("redo")

        self.assertEqual(self.dispatched, [])

    def test_hook_is_not_installed_when_disabled(self) -> None:
        self._enter_drawing_mode()

        self.assertIsNone(self.service._hook)


if __name__ == "__main__":
    unittest.main()

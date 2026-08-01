from __future__ import annotations

import unittest
from pathlib import Path

from config.settings import Settings


class SettingsTests(unittest.TestCase):
    def test_load_default_settings(self) -> None:
        settings = Settings.load(Path("config/settings.ini"))
        self.assertTrue(settings.overlay.click_through)
        self.assertTrue(settings.click_indicator.use_images)
        self.assertEqual(settings.click_indicator.image_directory, "resources/click_indicators")
        self.assertTrue(settings.click_indicator.show_left)
        self.assertTrue(settings.click_indicator.show_right)
        self.assertTrue(settings.click_indicator.show_both)
        self.assertTrue(settings.click_indicator.show_double)
        self.assertTrue(settings.click_indicator.show_wheel)
        self.assertTrue(settings.click_indicator.show_wheel_drag)
        self.assertEqual(settings.click_indicator.both_color, "#bf5af2")
        self.assertEqual(settings.click_indicator.image_size, 36)
        self.assertEqual(settings.click_indicator.image_gap, 10)
        self.assertEqual(settings.drawing.default_tool, "freehand")
        self.assertEqual(settings.drawing.line_style, "solid")
        self.assertEqual(settings.drawing.toolbar_button_size, 28)
        self.assertEqual(settings.drawing.toolbar_x, 20)
        self.assertEqual(settings.drawing.toolbar_y, 80)
        self.assertTrue(settings.drawing.pass_through_on_start)
        self.assertTrue(settings.capture.enabled)
        self.assertTrue(settings.capture.copy_to_clipboard)
        self.assertTrue(settings.notification.enabled)
        self.assertTrue(settings.notification.capture_completed)
        self.assertTrue(settings.notification.capture_failed)
        self.assertTrue(settings.notification.drawing_mode_changed)
        self.assertTrue(settings.notification.click_effects_changed)
        self.assertTrue(settings.pinned_window.enabled)
        self.assertEqual(settings.pinned_window.default_zoom, 1.0)
        self.assertTrue(settings.live_view.enabled)
        self.assertEqual(settings.live_view.default_fps, 10)
        self.assertFalse(settings.startup.enabled)
        self.assertEqual(settings.hotkeys.values["command_mode"], "Ctrl+Alt+A")
        self.assertEqual(settings.hotkeys.values["toggle_click_effects"], "Ctrl+Alt+E")
        self.assertNotIn("toggle_drawing", settings.hotkeys.values)
        self.assertNotIn("toggle_pause", settings.hotkeys.values)
        self.assertTrue(settings.command_mode.enabled)
        self.assertTrue(settings.command_mode.show_hint)
        self.assertEqual(settings.command_mode.timeout_ms, 5000)
        self.assertEqual(settings.command_mode.keys["toggle_overlay"], "O")
        self.assertEqual(settings.command_mode.keys["toggle_click_effects"], "E")
        self.assertEqual(settings.command_mode.keys["toggle_drawing"], "D")
        self.assertEqual(settings.command_mode.keys["clear_drawing"], "C")
        self.assertEqual(settings.command_mode.keys["pin_last_capture"], "B")
        self.assertEqual(settings.command_mode.keys["live_stop_all"], "X")
        self.assertEqual(settings.command_mode.keys["fullscreen_magnifier"], "F")
        self.assertEqual(settings.command_mode.keys["toggle_pause"], "Space")
        self.assertEqual(settings.region_selection.minimum_width, 4)
        self.assertTrue(settings.magnifier.enabled)
        self.assertEqual(settings.magnifier.scale, 2.0)


if __name__ == "__main__":
    unittest.main()

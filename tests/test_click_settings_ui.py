from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ClickSettingsUiTest(unittest.TestCase):
    def test_settings_dialog_exposes_all_click_indicator_toggles(self) -> None:
        source = (ROOT / "ui" / "settings_tabs.py").read_text(encoding="utf-8")
        source += (ROOT / "ui" / "settings_values.py").read_text(encoding="utf-8")

        for name in ("show_left", "show_right", "show_both", "show_wheel", "show_wheel_drag", "show_double"):
            self.assertIn(f"dialog.{name} = QCheckBox()", source)
            self.assertIn(f'"{name}"', source)
        self.assertIn("QGroupBox", source)
        self.assertIn("QGridLayout", source)
        self.assertIn("settings.click_indicator_options", source)
        self.assertIn('(tr("settings.show_double_click"), dialog.show_double)', source)
        self.assertNotIn('layout.addRow(tr("settings.show_double_click"), dialog.show_double)', source)
        self.assertIn('"settings.saved"', source)

    def test_settings_dialog_exposes_advanced_setting_tabs(self) -> None:
        source = (ROOT / "ui" / "settings_dialog.py").read_text(encoding="utf-8")
        source += (ROOT / "ui" / "settings_tabs.py").read_text(encoding="utf-8")
        source += (ROOT / "ui" / "settings_values.py").read_text(encoding="utf-8")
        source += (ROOT / "ui" / "settings_sections.py").read_text(encoding="utf-8")
        source += (ROOT / "locales" / "ko.ini").read_text(encoding="utf-8")

        for key in (
            "settings.tab.overlay",
            "settings.tab.pinned",
            "settings.tab.region",
            "settings.tab.hotkeys",
            "settings.tab.command_mode",
            "settings.tab.about",
            "settings.about_license",
            "settings.about_ai",
            "settings.open_user_manual",
            "settings.click_colors",
            "settings.filename_pattern",
            "settings.default_zoom",
            "settings.region_opacity",
            "settings.storage_mode",
            "settings.start_minimized",
            "settings.toolbar_button_size",
            "settings.save_and_close",
            "hotkey.command_mode",
            "hotkey.toggle_click_effects",
            "storage.portable",
            "capture_mode.region",
            "line_style.solid",
            "eraser_mode.object",
        ):
            self.assertIn(key, source)
        self.assertIn("QScrollArea", source)
        self.assertIn("QPushButton", source)
        self.assertIn('"manual.open"', source)
        self.assertIn("QDoubleSpinBox", source)
        self.assertIn("build_about_tab", source)
        self.assertIn("https://github.com/junossam/ScreenAid_Studio", source)
        self.assertIn("https://junossam.github.io/ScreenAid_Studio/", source)
        self.assertIn("reset_dialog_to_defaults", source)
        self.assertIn("settings.reset_defaults", source)
        self.assertIn("import_dialog_settings", source)
        self.assertIn("export_dialog_settings", source)
        self.assertIn("setWindowIcon", source)
        self.assertIn("tray_icon.ico", source)
        self.assertNotIn("dialog.command_mode_enabled = QCheckBox()", source)
        self.assertNotIn('layout.addRow(tr("settings.enable_command_mode")', source)
        self.assertIn("QFileDialog.getOpenFileName", source)
        self.assertIn("QFileDialog.getSaveFileName", source)
        self.assertIn("dialog.start_minimized = QCheckBox()", source)
        self.assertIn('dialog._set("app", "start_minimized"', source)
        self.assertIn('dialog._set("pinned_window", "default_zoom"', source)
        self.assertIn('dialog._set("region_selection", "dark_overlay_opacity"', source)
        self.assertIn('dialog._set("capture", "filename_pattern"', source)
        self.assertIn('dialog._set("drawing", "toolbar_button_size"', source)
        self.assertIn('dialog._set("hotkeys", name', source)
        self.assertIn('dialog._set("command_mode", name', source)
        self.assertIn("COMMAND_MODE_COMMANDS", source)
        self.assertIn("DEFAULT_HOTKEYS", source)
        self.assertIn("add_translated_items", source)
        self.assertIn("combo_data", source)
        self.assertIn("save_button.clicked.connect(lambda: self._save(False))", source)
        self.assertIn("save_close_button.clicked.connect(lambda: self._save(True))", source)
        self.assertIn("if close:", source)
        self.assertIn('dialog._set("command_mode", "enabled", True)', source)

    def test_click_effect_hotkey_is_runtime_only(self) -> None:
        source = (ROOT / "overlay" / "window.py").read_text(encoding="utf-8")
        source += (ROOT / "tray" / "tray_icon.py").read_text(encoding="utf-8")

        self.assertIn('"click_effects.toggle_temp"', source)
        self.assertIn("_click_effects_visible", source)
        self.assertIn("_click_effects_enabled", source)
        self.assertIn('"click_effects.temp.changed"', source)
        self.assertNotIn('self._set("click_indicator", "enabled", self._click_effects_visible)', source)

    def test_overlay_applies_click_settings_after_save(self) -> None:
        source = (ROOT / "overlay" / "window.py").read_text(encoding="utf-8")

        self.assertIn('self.bus.subscribe("settings.saved", self._settings_saved)', source)
        self.assertIn("show_both", source)
        self.assertIn("show_wheel_drag", source)
        self.assertIn("not self._click_effects_enabled()", source)
        self.assertIn("self.settings.click_indicator.enabled and self._click_effects_visible", source)

    def test_click_effect_follows_cursor_until_release(self) -> None:
        source = (ROOT / "overlay" / "window.py").read_text(encoding="utf-8")

        self.assertIn("_held_click_buttons", source)
        self.assertIn("hold_until_release=True", source)
        self.assertIn("self._move_click_effect(mouse_event)", source)
        self.assertIn("if not self._held_click_buttons:", source)
        self.assertIn("hold_until_ms=10**15 if hold_until_release", source)
        self.assertNotIn("MouseEventType.MOVE,\n            MouseEventType.WHEEL", source)


if __name__ == "__main__":
    unittest.main()

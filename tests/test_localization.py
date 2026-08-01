from __future__ import annotations

import unittest
from pathlib import Path

from core.localization import available_languages, configure_localization, tr


ROOT = Path(__file__).resolve().parents[1]


class LocalizationTest(unittest.TestCase):
    def test_korean_and_english_locale_files_are_available(self) -> None:
        languages = {language.code: language.name for language in available_languages(ROOT / "locales")}

        self.assertEqual("한국어", languages["ko"])
        self.assertEqual("English", languages["en"])

    def test_translation_uses_selected_language(self) -> None:
        configure_localization(ROOT / "locales", "ko")

        self.assertEqual("설정", tr("tray.settings"))
        self.assertEqual("프로그램 정보", tr("settings.tab.about"))
        self.assertEqual("settings.title.missing", tr("settings.title.missing"))

    def test_source_uses_translation_keys_for_primary_menus(self) -> None:
        tray = (ROOT / "tray" / "tray_icon.py").read_text(encoding="utf-8")
        settings = (ROOT / "ui" / "settings_dialog.py").read_text(encoding="utf-8")
        settings += (ROOT / "ui" / "settings_tabs.py").read_text(encoding="utf-8")
        pinned = (ROOT / "pinned" / "window.py").read_text(encoding="utf-8")
        live = (ROOT / "live_view" / "window.py").read_text(encoding="utf-8")

        self.assertIn('tr("tray.capture_region")', tray)
        self.assertIn('tr("settings.language")', settings)
        self.assertIn("build_notification_tab", settings)
        self.assertIn('tr("settings.notification_enabled")', settings)
        self.assertIn('tr("pinned.copy_annotated")', pinned)
        self.assertIn('tr("live.pin_current_frame")', live)


if __name__ == "__main__":
    unittest.main()

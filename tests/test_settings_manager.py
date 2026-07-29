from __future__ import annotations

import unittest
from configparser import ConfigParser
from pathlib import Path
from shutil import rmtree

from services.settings.settings_manager import SettingsManager, SettingsPaths

ROOT = Path(__file__).resolve().parents[1]


class SettingsManagerTests(unittest.TestCase):
    def test_loads_existing_settings_snapshot(self) -> None:
        settings_path = Path("config/settings.ini")
        manager = SettingsManager(SettingsPaths(settings_path, settings_path))

        settings = manager.load()

        self.assertTrue(settings.overlay.click_through)

    def test_load_defaults_parser_reads_default_file(self) -> None:
        settings_path = Path("config/settings.ini")
        manager = SettingsManager(SettingsPaths(settings_path, settings_path))

        parser = manager.load_defaults_parser()

        self.assertEqual(parser.get("hotkeys", "command_mode"), "Ctrl+Alt+A")

    def test_export_and_import_external_parser(self) -> None:
        root = ROOT / "tests" / ".tmp_settings_manager"
        if root.exists():
            rmtree(root)
        root.mkdir()
        try:
            defaults = root / "defaults.ini"
            user = root / "config.ini"
            export_path = root / "exported.ini"
            defaults.write_text("[app]\nlanguage = ko\n", encoding="utf-8")
            manager = SettingsManager(SettingsPaths(defaults, user))
            parser = ConfigParser()
            parser["app"] = {"language": "en"}

            manager.export_parser(parser, export_path)
            imported = manager.load_external_parser(export_path)

            self.assertEqual(imported.get("app", "language"), "en")
        finally:
            if root.exists():
                rmtree(root)

    def test_mirror_to_storage_mode_writes_portable_config(self) -> None:
        root = ROOT / "tests" / ".tmp_settings_storage"
        if root.exists():
            rmtree(root)
        defaults_dir = root / "config"
        defaults_dir.mkdir(parents=True)
        try:
            defaults = defaults_dir / "settings.ini"
            current = root / "current" / "config.ini"
            defaults.write_text("[storage]\nmode = portable\n", encoding="utf-8")
            manager = SettingsManager(SettingsPaths(defaults, current))
            parser = ConfigParser()
            parser["storage"] = {"mode": "portable"}

            target = manager.mirror_to_storage_mode(parser, "portable")

            self.assertEqual(target, root / "user_data" / "config.ini")
            self.assertTrue(target.exists())
        finally:
            if root.exists():
                rmtree(root)


if __name__ == "__main__":
    unittest.main()

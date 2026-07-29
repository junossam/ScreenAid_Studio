from __future__ import annotations

import unittest
from pathlib import Path
from shutil import rmtree
from unittest.mock import patch

from application.app_paths import resolve_app_paths

ROOT = Path(__file__).resolve().parents[1]


class AppPathsTests(unittest.TestCase):
    def test_default_paths_use_portable_user_data(self) -> None:
        root = ROOT / "tests" / ".tmp_app_paths_default"
        if root.exists():
            rmtree(root)
        root.mkdir(parents=True)
        try:
            appdata = root / "appdata"
            with patch.dict("os.environ", {"APPDATA": str(appdata)}):
                paths = resolve_app_paths(root)

            self.assertTrue(paths.portable)
            self.assertEqual(paths.config_path, root / "user_data" / "config.ini")
            self.assertFalse(hasattr(paths, "logs_dir"))
        finally:
            if root.exists():
                rmtree(root)

    def test_configured_appdata_paths_use_user_appdata(self) -> None:
        root = ROOT / "tests" / ".tmp_app_paths"
        if root.exists():
            rmtree(root)
        config_dir = root / "user_data"
        config_dir.mkdir(parents=True)
        (config_dir / "config.ini").write_text("[storage]\nmode = appdata\n", encoding="utf-8")
        try:
            appdata = root / "appdata"
            with patch.dict("os.environ", {"APPDATA": str(appdata)}):
                paths = resolve_app_paths(root)

            self.assertFalse(paths.portable)
            self.assertEqual(paths.config_path, appdata / "ScreenAidStudio" / "config.ini")
            self.assertFalse(hasattr(paths, "logs_dir"))
        finally:
            if root.exists():
                rmtree(root)


if __name__ == "__main__":
    unittest.main()

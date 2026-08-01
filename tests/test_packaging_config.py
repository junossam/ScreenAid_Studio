from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackagingConfigTests(unittest.TestCase):
    def test_pyinstaller_folder_distribution_config_is_present(self) -> None:
        spec = (ROOT / "ScreenAidStudio.spec").read_text(encoding="utf-8")
        build_script = (ROOT / "build_exe.ps1").read_text(encoding="utf-8")
        version_info = (ROOT / "version_info.txt").read_text(encoding="utf-8")

        self.assertIn('name="ScreenAidStudio"', spec)
        self.assertIn('contents_directory="internal"', spec)
        self.assertIn("console=False", spec)
        self.assertIn("uac_admin=False", spec)
        self.assertIn("resources\" / \"tray_icon.ico", spec)
        self.assertIn("datas=[]", spec)
        self.assertIn("pyi_rth_screenaid_paths.py", spec)
        self.assertIn("ScreenAidStudio.exe", build_script)
        self.assertIn("requirements-build.txt", build_script)
        self.assertIn("PyInstaller", build_script)
        self.assertIn("--contents-directory internal", build_script)
        self.assertIn("config\\settings.ini", build_script)
        self.assertIn("locales\\*.ini", build_script)
        self.assertIn("resources\\click_indicators\\*.png", build_script)
        self.assertIn("docs\\*.html", build_script)
        self.assertIn("docs\\manual.css", build_script)
        self.assertIn("'LICENSE', 'portable.flag'", build_script)
        self.assertIn("FileVersion', '0.2.1.1", version_info)
        self.assertIn("CompanyName', 'JunoSsam", version_info)

    def test_portable_flag_and_build_requirements_exist(self) -> None:
        self.assertTrue((ROOT / "portable.flag").exists())
        self.assertIn("PyInstaller", (ROOT / "requirements-build.txt").read_text(encoding="utf-8"))

    def test_default_build_opens_settings_window_on_startup(self) -> None:
        defaults = (ROOT / "config" / "settings.ini").read_text(encoding="utf-8")
        app_controller = (ROOT / "core" / "app_controller.py").read_text(encoding="utf-8")

        self.assertIn("start_minimized = false", defaults)
        self.assertIn("if not self.settings.app.start_minimized:", app_controller)
        self.assertIn('self.bus.publish("settings.open")', app_controller)


if __name__ == "__main__":
    unittest.main()

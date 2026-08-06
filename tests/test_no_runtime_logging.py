from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NoRuntimeLoggingTests(unittest.TestCase):
    def test_runtime_sources_do_not_configure_logging(self) -> None:
        forbidden = (
            "LogManager",
            "PrivacyLogFilter",
            "RotatingFileHandler",
            "logs_dir",
            "screen_assistant.log",
        )
        skipped = {"tests", "tools", "__pycache__", ".venv", ".tmp", "build", "dist"}
        findings: list[str] = []

        for path in ROOT.rglob("*.py"):
            relative = path.relative_to(ROOT)
            if relative.parts[0] in skipped:
                continue
            if str(relative).replace("\\", "/") == "core/diagnostics.py":
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in forbidden:
                if pattern in text:
                    findings.append(f"{relative}: {pattern}")

        self.assertEqual(findings, [])

    def test_developer_log_is_opt_in_by_file(self) -> None:
        source = (ROOT / "core" / "diagnostics.py").read_text(encoding="utf-8")

        self.assertIn('DEVELOPER_LOG_FILE = "developer.log"', source)
        self.assertIn("self.enabled = self.log_path.exists()", source)
        self.assertIn("except OSError:", source)
        self.assertIn("faulthandler.enable", source)
        self.assertIn("logging.FileHandler(self.log_path", source)

    def test_qt_runtime_uses_conservative_graphics_defaults(self) -> None:
        source = (ROOT / "core" / "qt_runtime.py").read_text(encoding="utf-8")
        runtime_hook = (ROOT / "hooks" / "pyi_rth_screenaid_paths.py").read_text(encoding="utf-8")

        for setting in ("QT_OPENGL", "QT_QUICK_BACKEND", "QT_ANGLE_PLATFORM"):
            self.assertIn(setting, source)
            self.assertIn(setting, runtime_hook)
        self.assertIn("QT_QPA_PLATFORM_PLUGIN_PATH", runtime_hook)

    def test_qt_widget_modules_are_imported_after_qapplication_creation(self) -> None:
        source = (ROOT / "app.py").read_text(encoding="utf-8")

        self.assertNotIn("from core.app_controller import AppController\n", source.split("def run", 1)[0])
        self.assertLess(source.index("app = QApplication([])"), source.index("from core.app_controller import AppController"))
        self.assertIn("Importing application controller", source)


if __name__ == "__main__":
    unittest.main()

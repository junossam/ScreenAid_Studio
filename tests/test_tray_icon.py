from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TrayIconTest(unittest.TestCase):
    def test_tray_activation_shows_menu_explicitly(self) -> None:
        source = (ROOT / "tray/tray_icon.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        methods: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "TrayIcon":
                methods = {item.name for item in node.body if isinstance(item, ast.FunctionDef)}
                break

        self.assertIn("_handle_activation", methods)
        self.assertIn("_show_menu", methods)
        self.assertIn("activated.connect", source)
        self.assertIn("ActivationReason.DoubleClick", source)
        self.assertIn("CommandId.OPEN_SETTINGS", source)
        self.assertIn("ActivationReason.Context", source)
        self.assertNotIn("ActivationReason.Trigger", source)
        self.assertIn("QAction(text, self._menu)", source)
        self.assertIn("QCursor.pos()", source)
        self.assertIn(".popup(", source)
        self.assertIn("CommandId.OPEN_USER_MANUAL", source)
        self.assertIn("tray.open_manual", source)
        self.assertIn("manual.failed", source)

    def test_tray_icon_restores_after_explorer_restart(self) -> None:
        source = (ROOT / "tray" / "tray_icon.py").read_text(encoding="utf-8")
        winapi = (ROOT / "utils" / "winapi.py").read_text(encoding="utf-8")

        self.assertIn("QAbstractNativeEventFilter", source)
        self.assertIn("_TaskbarCreatedFilter", source)
        self.assertIn("register_window_message", source)
        self.assertIn('"TaskbarCreated"', source)
        self.assertIn("installNativeEventFilter", source)
        self.assertIn("removeNativeEventFilter", source)
        self.assertIn("nativeEventFilter", source)
        self.assertIn("_restore_tray_icon", source)
        self.assertIn("restore_after_taskbar_created", source)
        self.assertIn("self._tray.show()", source)
        self.assertIn("RegisterWindowMessageW", winapi)

    def test_tray_icon_exposes_status_badges_and_tooltip(self) -> None:
        source = (ROOT / "tray" / "tray_icon.py").read_text(encoding="utf-8")
        locales = (ROOT / "locales" / "ko.ini").read_text(encoding="utf-8")

        self.assertIn("_refresh_status", source)
        self.assertIn("_status_icon", source)
        self.assertIn("_status_badges", source)
        self.assertIn("_status_texts", source)
        self.assertIn("setToolTip", source)
        self.assertIn("{tr('app.title')}(", source)
        self.assertIn("status.paused", source + locales)
        self.assertIn("status.drawing", source + locales)
        self.assertIn("status.click_effects_hidden", source + locales)
        self.assertIn("click_effects.temp.changed", source)
        self.assertIn("drawing.mode.changed", source)
        self.assertIn("app.pause.changed", source)
        self.assertIn("base_dir / \"resources\" / \"tray_icon.ico\"", source)


if __name__ == "__main__":
    unittest.main()

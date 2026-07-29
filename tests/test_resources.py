from __future__ import annotations

import unittest
from pathlib import Path


class ResourceTests(unittest.TestCase):
    def test_click_indicator_images_exist(self) -> None:
        base_dir = Path("resources/click_indicators")
        expected = {
            "left.png",
            "right.png",
            "double.png",
            "both.png",
            "middle.png",
            "wheel_up.png",
            "wheel_down.png",
            "wheel_left.png",
            "wheel_right.png",
        }

        existing = {path.name for path in base_dir.glob("*.png")}

        self.assertTrue(expected.issubset(existing))

    def test_tray_icon_exists(self) -> None:
        self.assertTrue(Path("resources/tray_icon.ico").exists())

    def test_overlay_loads_click_images_from_app_base_dir(self) -> None:
        source = Path("overlay/window.py").read_text(encoding="utf-8")
        container = Path("application/service_container.py").read_text(encoding="utf-8")

        self.assertIn("base_dir: Path", source)
        self.assertIn("self.base_dir / base_dir", source)
        self.assertIn("OverlayWindow(settings=settings, bus=event_bus, base_dir=base_dir)", container)


if __name__ == "__main__":
    unittest.main()

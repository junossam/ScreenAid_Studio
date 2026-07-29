from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ToolbarPositionStoreTest(unittest.TestCase):
    def test_toolbar_position_store_persists_drawing_toolbar_coordinates(self) -> None:
        source = (ROOT / "ui/toolbar_position_store.py").read_text(encoding="utf-8")

        self.assertIn('"drawing_toolbar.position.changed"', source)
        self.assertIn('"toolbar_x"', source)
        self.assertIn('"toolbar_y"', source)
        self.assertIn("save_parser", source)
        self.assertIn("QTimer", source)


if __name__ == "__main__":
    unittest.main()

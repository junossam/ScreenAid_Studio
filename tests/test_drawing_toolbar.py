from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DrawingToolbarTest(unittest.TestCase):
    def test_toolbar_publishes_tool_selection_and_dispatches_commands(self) -> None:
        source = (ROOT / "ui/drawing_toolbar.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        methods: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "DrawingToolbar":
                methods = {item.name for item in node.body if isinstance(item, ast.FunctionDef)}
                break

        self.assertIn("_select_tool", methods)
        self.assertIn("_select_color", methods)
        self.assertIn("_select_width", methods)
        self.assertIn("_select_line_style", methods)
        self.assertIn("_stamp_menu", methods)
        self.assertIn("_color_menu", methods)
        self.assertIn("_width_menu", methods)
        self.assertIn("_line_style_menu", methods)
        self.assertIn("_drawing_mode_changed", methods)
        self.assertIn("FloatingToolWindow", source)
        self.assertIn("ToolDragHandle", source)
        self.assertIn("tool_icon", source)
        self.assertIn("swatch_icon", source)
        self.assertIn("width_icon", source)
        self.assertIn("line_style_icon", source)
        self.assertIn("stamp_icon", source)
        self.assertIn("_color_button = QToolButton", source)
        self.assertIn("_width_button = QToolButton", source)
        self.assertIn("_style_button = QToolButton", source)
        self.assertIn("InstantPopup", source)
        self.assertIn("drawing.tool.select", source)
        self.assertIn("drawing.style.change", source)
        self.assertIn("CommandId.UNDO_DRAWING", source)
        self.assertIn("CommandId.DRAWING_PASS_THROUGH", source)
        self.assertIn("toolbar_button_size", source)
        self.assertIn("toolbar_x", source)
        self.assertIn("toolbar_y", source)
        self.assertIn("toolbar_metrics", source)
        self.assertIn("_apply_toolbar_size", source)
        self.assertIn("_toolbar_drag_finished", source)
        self.assertIn("drawing_toolbar.position.changed", source)
        self.assertIn("settings.saved", source)
        self.assertIn('"stamp_star", "tool.stamp"', source)
        self.assertIn("stamp_{value}", source)
        self.assertIn("mouse.blocking.suspended", source)


if __name__ == "__main__":
    unittest.main()

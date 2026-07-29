from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AnnotationToolbarTest(unittest.TestCase):
    def test_annotation_toolbar_exposes_tools_and_local_actions(self) -> None:
        source = (ROOT / "ui/annotation_toolbar.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        methods: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "AnnotationToolbar":
                methods = {item.name for item in node.body if isinstance(item, ast.FunctionDef)}
                break

        self.assertIn("set_current_tool", methods)
        self.assertIn("set_action_state", methods)
        self.assertIn("_select_tool", methods)
        self.assertIn("_select_color", methods)
        self.assertIn("_select_width", methods)
        self.assertIn("_select_line_style", methods)
        self.assertIn("_stamp_menu", methods)
        self.assertIn("_color_menu", methods)
        self.assertIn("_width_menu", methods)
        self.assertIn("_line_style_menu", methods)
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
        self.assertIn('"arrow", "tool.arrow"', source)
        self.assertIn('"ellipse", "tool.ellipse"', source)
        self.assertIn('"stamp_star", "tool.stamp"', source)
        self.assertIn("stamp_{value}", source)
        self.assertIn('"eraser", "tool.eraser"', source)
        self.assertIn("tr(", source)
        self.assertIn("toolbar_button_size", source)
        self.assertIn("toolbar_metrics", source)
        self.assertIn("apply_toolbar_size", source)


if __name__ == "__main__":
    unittest.main()

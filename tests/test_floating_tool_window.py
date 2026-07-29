from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FloatingToolWindowTest(unittest.TestCase):
    def test_floating_tool_window_supports_drag_handle_and_screen_clamping(self) -> None:
        source = (ROOT / "ui/floating_tool_window.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        methods: set[str] = set()
        classes: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes.add(node.name)
            if isinstance(node, ast.ClassDef) and node.name == "FloatingToolWindow":
                methods = {item.name for item in node.body if isinstance(item, ast.FunctionDef)}

        self.assertIn("move_near", methods)
        self.assertIn("move_to_available", methods)
        self.assertIn("ensure_inside_available", methods)
        self.assertIn("mousePressEvent", methods)
        self.assertIn("mouseMoveEvent", methods)
        self.assertIn("begin_drag", methods)
        self.assertIn("drag_to", methods)
        self.assertIn("end_drag", methods)
        self.assertIn("_clamp_point", methods)
        self.assertIn("drag_finished", source)
        self.assertIn("ToolDragHandle", classes)
        self.assertIn("QGuiApplication.screenAt", source)


if __name__ == "__main__":
    unittest.main()

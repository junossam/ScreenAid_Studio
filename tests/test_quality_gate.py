from __future__ import annotations

import unittest

from tools.quality_gate import FORBIDDEN_PATTERNS, iter_python_files


class QualityGateTests(unittest.TestCase):
    def test_forbidden_patterns_catch_high_risk_constructs(self) -> None:
        self.assertRegex("while " + "True:", FORBIDDEN_PATTERNS["while_true_polling"])
        self.assertRegex("ev" + "al(value)", FORBIDDEN_PATTERNS["dynamic_eval"])
        self.assertRegex("ex" + "ec(value)", FORBIDDEN_PATTERNS["dynamic_exec"])
        self.assertRegex("subprocess.run(cmd, shell=" + "True)", FORBIDDEN_PATTERNS["shell_true"])

    def test_dynamic_exec_rule_allows_qt_event_loop_method(self) -> None:
        self.assertIsNone(FORBIDDEN_PATTERNS["dynamic_exec"].search("app.exec()"))

    def test_iter_python_files_skips_generated_directories(self) -> None:
        names = {path.name for path in iter_python_files()}

        self.assertIn("main.py", names)
        self.assertNotIn("__init__.cpython-312.pyc", names)


if __name__ == "__main__":
    unittest.main()

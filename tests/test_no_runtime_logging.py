from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NoRuntimeLoggingTests(unittest.TestCase):
    def test_runtime_sources_do_not_configure_logging(self) -> None:
        forbidden = (
            "import logging",
            "logging.",
            "getLogger",
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
            text = path.read_text(encoding="utf-8")
            for pattern in forbidden:
                if pattern in text:
                    findings.append(f"{relative}: {pattern}")

        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()

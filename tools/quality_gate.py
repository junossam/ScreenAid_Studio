from __future__ import annotations

import argparse
import compileall
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIPPED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tmp",
    ".venv",
    "__pycache__",
    "build",
    "cache",
    "dist",
    "logs",
}


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    passed: bool
    detail: str
    required: bool = True


FORBIDDEN_PATTERNS = {
    "while_true_polling": re.compile(r"\bwhile\s+True\s*:"),
    "dynamic_eval": re.compile(r"(?<!\.)\beval\s*\("),
    "dynamic_exec": re.compile(r"(?<!\.)\bexec\s*\("),
    "shell_true": re.compile(r"\bshell\s*=\s*True\b"),
}


def iter_python_files(root: Path = ROOT) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in SKIPPED_DIRS for part in path.relative_to(root).parts):
            continue
        files.append(path)
    return sorted(files)


def scan_forbidden_patterns(root: Path = ROOT) -> CheckResult:
    findings: list[str] = []
    for path in iter_python_files(root):
        text = path.read_text(encoding="utf-8")
        for index, line in enumerate(text.splitlines(), start=1):
            for rule, pattern in FORBIDDEN_PATTERNS.items():
                if pattern.search(line):
                    rel = path.relative_to(root)
                    findings.append(f"{rel}:{index} {rule}")
    if findings:
        return CheckResult("forbidden-patterns", False, "\n".join(findings))
    return CheckResult("forbidden-patterns", True, "no forbidden patterns found")


def run_unittest() -> CheckResult:
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    detail = (result.stdout + result.stderr).strip()
    return CheckResult("unittest", result.returncode == 0, detail or "ok")


def run_compileall() -> CheckResult:
    skipped = "|".join(re.escape(part) for part in sorted(SKIPPED_DIRS))
    passed = compileall.compile_dir(str(ROOT), quiet=1, force=False, rx=re.compile(rf"[\\/](?:{skipped})(?:[\\/]|$)"))
    return CheckResult("compileall", passed, "ok" if passed else "compile failed")


def run_optional_module(module: str) -> CheckResult:
    exists = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if exists.returncode != 0:
        return CheckResult(module, True, "skipped: module not installed", required=False)

    command = [sys.executable, "-m", module, "check", "."] if module == "ruff" else [sys.executable, "-m", module, "."]
    result = subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True)
    detail = (result.stdout + result.stderr).strip()
    return CheckResult(module, result.returncode == 0, detail or "ok", required=False)


def run_quality_gate(*, include_optional: bool = False) -> list[CheckResult]:
    checks = [scan_forbidden_patterns(), run_unittest(), run_compileall()]
    if include_optional:
        checks.extend([run_optional_module("ruff"), run_optional_module("mypy")])
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ScreenAid Studio quality gates.")
    parser.add_argument("--full", action="store_true", help="include optional ruff and mypy checks")
    args = parser.parse_args()

    failed = False
    for check in run_quality_gate(include_optional=args.full):
        status = "PASS" if check.passed else "FAIL"
        optional = " optional" if not check.required else ""
        print(f"[{status}]{optional} {check.name}")
        if check.detail:
            print(check.detail)
        if check.required and not check.passed:
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

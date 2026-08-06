from __future__ import annotations

import sys
from pathlib import Path

from core.diagnostics import setup_diagnostics
from core.qt_runtime import configure_qt_runtime_environment


def application_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


if __name__ == "__main__":
    base_dir = application_base_dir()
    diagnostics = setup_diagnostics(base_dir)
    try:
        configure_qt_runtime_environment()
        diagnostics.info("Configured Qt runtime environment")
        diagnostics.info("Importing app module")
        from app import run

        diagnostics.info("Imported app module")
        diagnostics.info("Calling app.run")
        sys.exit(run(base_dir, diagnostics=diagnostics))
    except Exception as exc:
        diagnostics.exception("Application startup failed", exc)
        raise

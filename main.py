from __future__ import annotations

import sys
from pathlib import Path

from app import run


def application_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


if __name__ == "__main__":
    sys.exit(run(application_base_dir()))

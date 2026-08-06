from __future__ import annotations

import os


def configure_qt_runtime_environment() -> None:
    os.environ.setdefault("QT_OPENGL", "software")
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    os.environ.setdefault("QT_ANGLE_PLATFORM", "warp")

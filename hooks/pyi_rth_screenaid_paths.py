from __future__ import annotations

import os
import sys
from pathlib import Path


def _add_dll_directory(path: Path) -> None:
    if not path.exists():
        return
    text = str(path)
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(text)
    current_path = os.environ.get("PATH", "")
    parts = current_path.split(os.pathsep) if current_path else []
    if text not in parts:
        os.environ["PATH"] = text + (os.pathsep + current_path if current_path else "")


def _runtime_base_dirs() -> list[Path]:
    exe_dir = Path(sys.executable).resolve().parent
    bases = [Path(getattr(sys, "_MEIPASS", exe_dir)).resolve(), exe_dir, exe_dir / "_internal"]
    unique: list[Path] = []
    for base in bases:
        if base not in unique:
            unique.append(base)
    return unique


for base_dir in _runtime_base_dirs():
    _add_dll_directory(base_dir)
    _add_dll_directory(base_dir / "PySide6")
    _add_dll_directory(base_dir / "shiboken6")

    plugins_dir = base_dir / "PySide6" / "plugins"
    if plugins_dir.exists():
        os.environ.setdefault("QT_PLUGIN_PATH", str(plugins_dir))

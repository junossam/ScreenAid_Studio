from __future__ import annotations

import os
import sys
from pathlib import Path


os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_ANGLE_PLATFORM", "warp")


def _developer_log_path() -> Path:
    return Path(sys.executable).resolve().parent / "developer.log"


def _runtime_log(message: str) -> None:
    log_path = _developer_log_path()
    if not log_path.exists():
        return
    try:
        with log_path.open("a", encoding="utf-8") as file:
            file.write(f"[runtime-hook] {message}\n")
    except OSError:
        pass


def _add_dll_directory(path: Path) -> None:
    if not path.exists():
        _runtime_log(f"missing dll directory: {path}")
        return
    text = str(path)
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(text)
    current_path = os.environ.get("PATH", "")
    parts = current_path.split(os.pathsep) if current_path else []
    if text not in parts:
        os.environ["PATH"] = text + (os.pathsep + current_path if current_path else "")
    _runtime_log(f"added dll directory: {path}")


def _runtime_base_dirs() -> list[Path]:
    exe_dir = Path(sys.executable).resolve().parent
    bases = [Path(getattr(sys, "_MEIPASS", exe_dir)).resolve(), exe_dir, exe_dir / "internal", exe_dir / "_internal"]
    unique: list[Path] = []
    for base in bases:
        if base not in unique:
            unique.append(base)
    return unique


for base_dir in _runtime_base_dirs():
    _runtime_log(f"checking runtime base: {base_dir}")
    _add_dll_directory(base_dir)
    _add_dll_directory(base_dir / "PySide6")
    _add_dll_directory(base_dir / "shiboken6")

    plugins_dir = base_dir / "PySide6" / "plugins"
    if plugins_dir.exists():
        os.environ.setdefault("QT_PLUGIN_PATH", str(plugins_dir))
        os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", str(plugins_dir / "platforms"))
        _runtime_log(f"QT_PLUGIN_PATH={os.environ.get('QT_PLUGIN_PATH', '')}")
        _runtime_log(f"QT_QPA_PLATFORM_PLUGIN_PATH={os.environ.get('QT_QPA_PLATFORM_PLUGIN_PATH', '')}")

_runtime_log(f"QT_OPENGL={os.environ.get('QT_OPENGL', '')}")
_runtime_log(f"QT_QUICK_BACKEND={os.environ.get('QT_QUICK_BACKEND', '')}")
_runtime_log(f"QT_ANGLE_PLATFORM={os.environ.get('QT_ANGLE_PLATFORM', '')}")

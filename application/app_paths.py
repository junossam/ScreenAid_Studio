from __future__ import annotations

import os
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path

STORAGE_APPDATA = "appdata"
STORAGE_PORTABLE = "portable"


@dataclass(frozen=True, slots=True)
class AppPaths:
    base_dir: Path
    data_dir: Path
    config_path: Path
    cache_dir: Path
    portable: bool


def appdata_data_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    return (Path(appdata) if appdata else Path.home() / "AppData" / "Roaming") / "ScreenAidStudio"


def portable_data_dir(base_dir: Path) -> Path:
    return base_dir.resolve() / "user_data"


def data_dir_for_storage_mode(base_dir: Path, mode: str) -> Path:
    if normalize_storage_mode(mode) == STORAGE_APPDATA:
        return appdata_data_dir()
    return portable_data_dir(base_dir)


def normalize_storage_mode(mode: str) -> str:
    text = (mode or STORAGE_PORTABLE).strip().lower()
    if text == STORAGE_APPDATA:
        return STORAGE_APPDATA
    return STORAGE_PORTABLE


def resolve_app_paths(base_dir: Path) -> AppPaths:
    base_dir = base_dir.resolve()
    mode = _configured_storage_mode(base_dir)
    data_dir = data_dir_for_storage_mode(base_dir, mode)

    return AppPaths(
        base_dir=base_dir,
        data_dir=data_dir,
        config_path=data_dir / "config.ini",
        cache_dir=data_dir / "cache",
        portable=mode == STORAGE_PORTABLE,
    )


def _configured_storage_mode(base_dir: Path) -> str:
    if (base_dir / "portable.flag").exists():
        return STORAGE_PORTABLE
    for config_path in (portable_data_dir(base_dir) / "config.ini", appdata_data_dir() / "config.ini"):
        mode = _read_storage_mode(config_path)
        if mode:
            return mode
    return STORAGE_PORTABLE


def _read_storage_mode(path: Path) -> str | None:
    if not path.exists():
        return None
    parser = ConfigParser()
    try:
        parser.read(path, encoding="utf-8")
    except Exception:
        return None
    if not parser.has_section("storage"):
        return None
    return normalize_storage_mode(parser.get("storage", "mode", fallback=STORAGE_PORTABLE))

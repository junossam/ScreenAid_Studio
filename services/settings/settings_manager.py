from __future__ import annotations

import os
import shutil
from configparser import ConfigParser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from application.app_paths import data_dir_for_storage_mode, normalize_storage_mode
from config.settings import Settings


@dataclass(frozen=True, slots=True)
class SettingsPaths:
    defaults_path: Path
    user_path: Path


class SettingsManager:
    MAX_IMPORT_BYTES = 1024 * 1024

    def __init__(self, paths: SettingsPaths) -> None:
        self.paths = paths

    def load(self) -> Settings:
        self._ensure_user_settings()
        try:
            return Settings.load(self.paths.user_path)
        except Exception:
            backup = self.paths.user_path.with_suffix(".broken.ini")
            if self.paths.user_path.exists():
                shutil.copy2(self.paths.user_path, backup)
            if self._restore_from_defaults():
                return Settings.load(self.paths.user_path)
            # No usable defaults file either - drop the unreadable user
            # config so Settings.load() falls back to its built-in defaults
            # instead of leaving the app permanently unable to start.
            self.paths.user_path.unlink(missing_ok=True)
            return Settings.load(self.paths.user_path)

    def _ensure_user_settings(self) -> None:
        self.paths.user_path.parent.mkdir(parents=True, exist_ok=True)
        if self.paths.user_path.exists():
            return
        self._restore_from_defaults()

    def _restore_from_defaults(self) -> bool:
        if self.paths.defaults_path.resolve() == self.paths.user_path.resolve():
            return False
        if not self.paths.defaults_path.exists():
            return False
        shutil.copy2(self.paths.defaults_path, self.paths.user_path)
        return True

    def load_parser(self) -> ConfigParser:
        self._ensure_user_settings()
        parser = ConfigParser()
        parser.read(self.paths.user_path, encoding="utf-8")
        return parser

    def load_defaults_parser(self) -> ConfigParser:
        parser = ConfigParser()
        parser.read(self.paths.defaults_path, encoding="utf-8")
        return parser

    def load_external_parser(self, path: Path) -> ConfigParser:
        if path.stat().st_size > self.MAX_IMPORT_BYTES:
            raise ValueError("Settings file is too large")
        parser = ConfigParser()
        read_files = parser.read(path, encoding="utf-8")
        if not read_files or not parser.sections():
            raise ValueError("Settings file is empty or invalid")
        return parser

    def export_parser(self, parser: ConfigParser, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            parser.write(file)

    def save_parser(self, parser: ConfigParser) -> None:
        self.paths.user_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.paths.user_path.with_suffix(".tmp")
        backup_path = self._backup_path()
        with temp_path.open("w", encoding="utf-8") as file:
            parser.write(file)
            file.flush()
            os.fsync(file.fileno())
        if self.paths.user_path.exists():
            shutil.copy2(self.paths.user_path, backup_path)
        os.replace(temp_path, self.paths.user_path)
        self._prune_backups()

    def update_option(self, section: str, option: str, value: object) -> None:
        parser = self.load_parser()
        if not parser.has_section(section):
            parser.add_section(section)
        parser.set(section, option, str(value))
        self.save_parser(parser)

    def mirror_to_storage_mode(self, parser: ConfigParser, mode: str) -> Path:
        base_dir = self.paths.defaults_path.parent.parent
        target_path = data_dir_for_storage_mode(base_dir, normalize_storage_mode(mode)) / "config.ini"
        if target_path.resolve() != self.paths.user_path.resolve():
            self.export_parser(parser, target_path)
        return target_path

    def _backup_path(self) -> Path:
        backups_dir = self.paths.user_path.parent / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return backups_dir / f"config_{stamp}.ini"

    def _prune_backups(self, keep: int = 5) -> None:
        backups_dir = self.paths.user_path.parent / "backups"
        backups = sorted(backups_dir.glob("config_*.ini"), key=lambda path: path.stat().st_mtime, reverse=True)
        for backup in backups[keep:]:
            backup.unlink(missing_ok=True)

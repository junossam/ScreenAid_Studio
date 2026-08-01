from __future__ import annotations

import ctypes
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from application.app_paths import resolve_app_paths
from core.app_controller import AppController
from core.dpi import enable_per_monitor_v2
from core.localization import configure_localization
from core.single_instance import SingleInstanceLock
from services.settings.settings_manager import SettingsManager, SettingsPaths


APP_NAME = "ScreenAid Studio"
APP_USER_MODEL_ID = APP_NAME


def run(base_dir: Path) -> int:
    paths = resolve_app_paths(base_dir)
    instance_lock = SingleInstanceLock()
    if not instance_lock.acquire():
        return 0
    try:
        enable_per_monitor_v2()
        _set_windows_app_id()

        settings_manager = SettingsManager(
            SettingsPaths(
                defaults_path=base_dir / "config" / "settings.ini",
                user_path=paths.config_path,
            )
        )
        settings = settings_manager.load()
        configure_localization(base_dir / "locales", settings.app.language)
        app = QApplication([])
        app.setApplicationName(APP_NAME)
        app.setApplicationDisplayName(APP_NAME)
        app.setOrganizationName("JunoSsam")
        app.setWindowIcon(QIcon(str(base_dir / "resources" / "tray_icon.ico")))
        app.setQuitOnLastWindowClosed(False)

        controller = AppController(settings=settings, base_dir=base_dir, settings_manager=settings_manager)
        controller.start()

        return app.exec()
    finally:
        instance_lock.release()


def _set_windows_app_id() -> None:
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass

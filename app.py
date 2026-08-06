from __future__ import annotations

import ctypes
from pathlib import Path

from application.app_paths import resolve_app_paths
from core.diagnostics import Diagnostics
from core.dpi import enable_per_monitor_v2
from core.localization import configure_localization
from core.single_instance import SingleInstanceLock
from services.settings.settings_manager import SettingsManager, SettingsPaths


APP_NAME = "ScreenAid Studio"
APP_USER_MODEL_ID = APP_NAME


def run(base_dir: Path, diagnostics: Diagnostics | None = None) -> int:
    if diagnostics is not None:
        diagnostics.info("Resolving application paths")
    paths = resolve_app_paths(base_dir)
    instance_lock = SingleInstanceLock()
    if diagnostics is not None:
        diagnostics.info(f"Data directory: {paths.data_dir}")
        diagnostics.info(f"Config path: {paths.config_path}")
        diagnostics.info("Acquiring single instance lock")
    if not instance_lock.acquire():
        if diagnostics is not None:
            diagnostics.info("Another instance is already running")
        return 0
    try:
        if diagnostics is not None:
            diagnostics.info("Enabling DPI awareness")
        enable_per_monitor_v2()
        _set_windows_app_id()

        if diagnostics is not None:
            diagnostics.info("Loading settings")
        settings_manager = SettingsManager(
            SettingsPaths(
                defaults_path=base_dir / "config" / "settings.ini",
                user_path=paths.config_path,
            )
        )
        settings = settings_manager.load()
        configure_localization(base_dir / "locales", settings.app.language)
        if diagnostics is not None:
            diagnostics.info("Importing Qt application classes")
        from PySide6.QtGui import QIcon
        from PySide6.QtWidgets import QApplication

        if diagnostics is not None:
            diagnostics.info("Creating QApplication")
        app = QApplication([])
        app.setApplicationName(APP_NAME)
        app.setApplicationDisplayName(APP_NAME)
        app.setOrganizationName("JunoSsam")
        app.setWindowIcon(QIcon(str(base_dir / "resources" / "tray_icon.ico")))
        app.setQuitOnLastWindowClosed(False)

        if diagnostics is not None:
            diagnostics.info("Importing application controller")
        from core.app_controller import AppController

        if diagnostics is not None:
            diagnostics.info("Starting services")
        controller = AppController(settings=settings, base_dir=base_dir, settings_manager=settings_manager)
        controller.start()

        if diagnostics is not None:
            diagnostics.info("Entering Qt event loop")
        exit_code = app.exec()
        if diagnostics is not None:
            diagnostics.info(f"Qt event loop exited: {exit_code}")
        return exit_code
    except Exception as exc:
        if diagnostics is not None:
            diagnostics.exception("Application run failed", exc)
        raise
    finally:
        instance_lock.release()
        if diagnostics is not None:
            diagnostics.info("Single instance lock released")


def _set_windows_app_id() -> None:
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass

from __future__ import annotations

import logging
import faulthandler
import platform
import sys
import threading
import traceback
from pathlib import Path
from types import TracebackType


DEVELOPER_LOG_FILE = "developer.log"


class Diagnostics:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir.resolve()
        self.log_path = self.base_dir / DEVELOPER_LOG_FILE
        self.enabled = self.log_path.exists()
        self._logger: logging.Logger | None = None
        self._fault_file = None

    def install(self) -> None:
        if not self.enabled:
            return
        self._logger = logging.getLogger("ScreenAidStudio")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        self._logger.handlers.clear()
        try:
            handler = logging.FileHandler(self.log_path, encoding="utf-8")
        except OSError:
            self.enabled = False
            self._logger = None
            return
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        self._logger.addHandler(handler)
        self._enable_fault_handler()
        sys.excepthook = self._excepthook
        if hasattr(threading, "excepthook"):
            threading.excepthook = self._threading_excepthook
        self.info("Developer diagnostics enabled")
        self.info(f"Base directory: {self.base_dir}")
        self.info(f"Executable: {sys.executable}")
        self.info(f"Frozen: {getattr(sys, 'frozen', False)}")
        self.info(f"Python: {sys.version}")
        self.info(f"Platform: {platform.platform()}")

    def info(self, message: str) -> None:
        if self._logger is not None:
            self._logger.info(message)

    def exception(self, message: str, exc: BaseException) -> None:
        if self._logger is not None:
            self._logger.exception(message, exc_info=(type(exc), exc, exc.__traceback__))

    def _excepthook(
        self,
        exc_type: type[BaseException],
        exc: BaseException,
        tb: TracebackType | None,
    ) -> None:
        if self._logger is not None:
            text = "".join(traceback.format_exception(exc_type, exc, tb))
            self._logger.critical("Unhandled exception\n%s", text)
        sys.__excepthook__(exc_type, exc, tb)

    def _threading_excepthook(self, args) -> None:
        if self._logger is not None:
            text = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
            self._logger.critical("Unhandled thread exception in %s\n%s", args.thread.name, text)

    def _enable_fault_handler(self) -> None:
        try:
            self._fault_file = self.log_path.open("a", encoding="utf-8")
            faulthandler.enable(file=self._fault_file, all_threads=True)
        except Exception:
            self._fault_file = None


def setup_diagnostics(base_dir: Path) -> Diagnostics:
    diagnostics = Diagnostics(base_dir)
    diagnostics.install()
    return diagnostics

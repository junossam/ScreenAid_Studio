from __future__ import annotations

from core.service import Service


class MagnifierWindow(Service):
    def __init__(self) -> None:
        self._running = False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False


from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ApplicationState:
    is_running: bool = False
    is_paused: bool = False
    overlay_visible: bool = False
    drawing_pass_through: bool = True


class ApplicationStateStore:
    def __init__(self) -> None:
        self._state = ApplicationState()

    @property
    def state(self) -> ApplicationState:
        return self._state

    def set_running(self, value: bool) -> None:
        self._state.is_running = value

    def set_paused(self, value: bool) -> None:
        self._state.is_paused = value

    def set_overlay_visible(self, value: bool) -> None:
        self._state.overlay_visible = value

    def set_drawing_pass_through(self, value: bool) -> None:
        self._state.drawing_pass_through = value

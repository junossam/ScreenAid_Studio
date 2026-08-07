from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

CommandHandler = Callable[..., None]
_LOGGER = logging.getLogger("ScreenAidStudio")


@dataclass(slots=True)
class CommandResult:
    command_id: str
    handled: bool
    error: str | None = None


@dataclass
class CommandDispatcher:
    _handlers: dict[str, CommandHandler] = field(default_factory=dict)

    def register(self, command_id: str, handler: CommandHandler) -> None:
        self._handlers[command_id] = handler

    def dispatch(self, command_id: str, **payload: Any) -> CommandResult:
        handler = self._handlers.get(command_id)
        if handler is None:
            return CommandResult(command_id=command_id, handled=False, error="Unhandled command")
        try:
            handler(**payload)
        except Exception as exc:
            _LOGGER.exception("Command handler for %s raised an exception", command_id)
            return CommandResult(command_id=command_id, handled=True, error=str(exc))
        return CommandResult(command_id=command_id, handled=True)

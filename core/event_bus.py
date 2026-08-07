from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, DefaultDict
from uuid import uuid4

# Only emits output when core.diagnostics.Diagnostics has attached a handler
# (i.e. developer.log exists next to main.py) - silent otherwise, per
# NFR-PRIV-001 (no runtime log files in normal use).
_LOGGER = logging.getLogger("ScreenAidStudio")


@dataclass(frozen=True)
class Event:
    name: str
    payload: dict[str, Any]


EventHandler = Callable[[Event], None]


@dataclass(frozen=True)
class Subscription:
    token: str
    event_name: str


class EventBus:
    def __init__(self) -> None:
        self._handlers: DefaultDict[str, list[EventHandler]] = defaultdict(list)
        self._tokens: dict[str, tuple[str, EventHandler]] = {}

    def subscribe(self, name: str, handler: EventHandler) -> Subscription:
        self._handlers[name].append(handler)
        token = uuid4().hex
        self._tokens[token] = (name, handler)
        return Subscription(token=token, event_name=name)

    def unsubscribe(self, subscription: Subscription) -> None:
        entry = self._tokens.pop(subscription.token, None)
        if entry is None:
            return
        name, handler = entry
        if handler in self._handlers.get(name, ()):
            self._handlers[name].remove(handler)

    def publish(self, name: str, **payload: Any) -> None:
        event = Event(name=name, payload=payload)
        for handler in tuple(self._handlers.get(name, ())):
            try:
                handler(event)
            except Exception:
                _LOGGER.exception("Event handler for %s raised an exception", name)

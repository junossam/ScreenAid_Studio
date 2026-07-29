from __future__ import annotations

import unittest

from core.event_bus import EventBus


class EventBusTests(unittest.TestCase):
    def test_publish_subscribe(self) -> None:
        bus = EventBus()
        seen = []
        bus.subscribe("x", lambda event: seen.append(event.payload["value"]))
        bus.publish("x", value=7)
        self.assertEqual(seen, [7])

    def test_unsubscribe(self) -> None:
        bus = EventBus()
        seen = []
        subscription = bus.subscribe("x", lambda event: seen.append(event.payload["value"]))
        bus.unsubscribe(subscription)
        bus.publish("x", value=7)
        self.assertEqual(seen, [])

    def test_handler_failure_does_not_stop_other_handlers(self) -> None:
        bus = EventBus()
        seen = []

        def failing_handler(_event) -> None:
            raise RuntimeError("handler failed")

        bus.subscribe("x", failing_handler)
        bus.subscribe("x", lambda event: seen.append(event.payload["value"]))

        bus.publish("x", value=7)

        self.assertEqual(seen, [7])


if __name__ == "__main__":
    unittest.main()

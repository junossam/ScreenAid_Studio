from __future__ import annotations

import unittest

from application.command_dispatcher import CommandDispatcher
from application.commands import CommandId


class CommandDispatcherTests(unittest.TestCase):
    def test_dispatch_registered_command(self) -> None:
        dispatcher = CommandDispatcher()
        seen = []
        dispatcher.register(CommandId.CLEAR_DRAWING, lambda: seen.append("clear"))

        result = dispatcher.dispatch(CommandId.CLEAR_DRAWING)

        self.assertTrue(result.handled)
        self.assertIsNone(result.error)
        self.assertEqual(seen, ["clear"])

    def test_unhandled_command_returns_result(self) -> None:
        result = CommandDispatcher().dispatch("missing")

        self.assertFalse(result.handled)
        self.assertIsNotNone(result.error)


if __name__ == "__main__":
    unittest.main()

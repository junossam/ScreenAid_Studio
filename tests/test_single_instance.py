from __future__ import annotations

import unittest
from uuid import uuid4

from core.single_instance import SingleInstanceLock


class SingleInstanceLockTests(unittest.TestCase):
    def test_second_lock_for_same_name_is_rejected(self) -> None:
        name = f"Local\\ScreenAssistantTest-{uuid4().hex}"
        first = SingleInstanceLock(name)
        second = SingleInstanceLock(name)
        try:
            self.assertTrue(first.acquire())
            self.assertFalse(second.acquire())
        finally:
            second.release()
            first.release()


if __name__ == "__main__":
    unittest.main()

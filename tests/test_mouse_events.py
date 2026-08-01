from __future__ import annotations

import unittest

from mouse.events import MouseEvent, MouseEventType
from mouse.hook import GlobalMouseHook
from overlay.effects import ClickButtonTracker, ClickEffectType
from core.event_bus import EventBus


class MouseEventTests(unittest.TestCase):
    def test_mouse_event_is_immutable_value(self) -> None:
        event = MouseEvent(MouseEventType.WHEEL, 10, 20, 30, wheel_delta=120)
        self.assertEqual(event.event_type, MouseEventType.WHEEL)
        self.assertEqual(event.wheel_delta, 120)
        self.assertFalse(event.injected)

    def test_left_right_combination_becomes_both_click(self) -> None:
        tracker = ClickButtonTracker()
        left = MouseEvent(MouseEventType.LEFT_DOWN, 10, 20, 30)
        right = MouseEvent(MouseEventType.RIGHT_DOWN, 10, 20, 31)

        self.assertEqual(tracker.apply(left), ClickEffectType.LEFT)
        self.assertEqual(tracker.apply(right), ClickEffectType.BOTH)

    def test_right_left_combination_becomes_both_click(self) -> None:
        tracker = ClickButtonTracker()
        right = MouseEvent(MouseEventType.RIGHT_DOWN, 10, 20, 30)
        left = MouseEvent(MouseEventType.LEFT_DOWN, 10, 20, 31)

        self.assertEqual(tracker.apply(right), ClickEffectType.RIGHT)
        self.assertEqual(tracker.apply(left), ClickEffectType.BOTH)

    def test_basic_double_click_is_detected(self) -> None:
        tracker = ClickButtonTracker()
        first = MouseEvent(MouseEventType.LEFT_DOWN, 10, 20, 30)
        second = MouseEvent(MouseEventType.LEFT_DOWN, 12, 21, 200)

        self.assertEqual(tracker.apply(first), ClickEffectType.LEFT)
        self.assertEqual(tracker.apply(second), ClickEffectType.DOUBLE)

    def test_release_updates_pressed_state(self) -> None:
        tracker = ClickButtonTracker()
        tracker.apply(MouseEvent(MouseEventType.LEFT_DOWN, 10, 20, 30))
        tracker.apply(MouseEvent(MouseEventType.LEFT_UP, 10, 20, 31))

        self.assertFalse(tracker.left_pressed)

    def test_middle_button_drag_is_throttled_as_wheel_drag(self) -> None:
        tracker = ClickButtonTracker()
        down = MouseEvent(MouseEventType.MIDDLE_DOWN, 10, 20, 30)
        early_move = MouseEvent(MouseEventType.MOVE, 11, 21, 60)
        later_move = MouseEvent(MouseEventType.MOVE, 20, 30, 120)

        self.assertEqual(tracker.apply(down), ClickEffectType.MIDDLE)
        self.assertIsNone(tracker.apply(early_move))
        self.assertEqual(tracker.apply(later_move), ClickEffectType.MIDDLE)

    def test_drawing_blocking_does_not_block_cursor_move(self) -> None:
        hook = GlobalMouseHook(EventBus())
        hook._block_overlay_input = True

        self.assertTrue(hook._should_block(MouseEvent(MouseEventType.LEFT_DOWN, 10, 20, 30)))
        self.assertFalse(hook._should_block(MouseEvent(MouseEventType.MOVE, 11, 21, 31)))

    def test_drag_move_is_emitted_for_pressed_mouse_buttons(self) -> None:
        hook = GlobalMouseHook(EventBus())

        self.assertTrue(hook._should_emit(MouseEvent(MouseEventType.LEFT_DOWN, 10, 20, 30)))
        self.assertTrue(hook._should_emit(MouseEvent(MouseEventType.MOVE, 11, 21, 31)))
        self.assertTrue(hook._should_emit(MouseEvent(MouseEventType.LEFT_UP, 11, 21, 32)))

        self.assertTrue(hook._should_emit(MouseEvent(MouseEventType.RIGHT_DOWN, 10, 20, 40)))
        self.assertTrue(hook._should_emit(MouseEvent(MouseEventType.MOVE, 12, 22, 41)))
        self.assertTrue(hook._should_emit(MouseEvent(MouseEventType.RIGHT_UP, 12, 22, 42)))

        self.assertTrue(hook._should_emit(MouseEvent(MouseEventType.MIDDLE_DOWN, 10, 20, 50)))
        self.assertTrue(hook._should_emit(MouseEvent(MouseEventType.MOVE, 13, 23, 51)))
        self.assertTrue(hook._should_emit(MouseEvent(MouseEventType.MIDDLE_UP, 13, 23, 52)))

    def test_toolbar_and_popup_events_are_not_emitted_as_drawing_input(self) -> None:
        hook = GlobalMouseHook(EventBus())
        hook._input_exclusions["toolbar"] = (0, 0, 100, 100)

        self.assertFalse(hook._should_emit(MouseEvent(MouseEventType.LEFT_DOWN, 10, 20, 30)))
        self.assertFalse(hook._should_emit(MouseEvent(MouseEventType.MOVE, 11, 21, 31)))
        self.assertFalse(hook._should_emit(MouseEvent(MouseEventType.LEFT_UP, 11, 21, 32)))

        hook._blocking_suspended = True
        self.assertFalse(hook._should_emit(MouseEvent(MouseEventType.LEFT_DOWN, 200, 200, 40)))


if __name__ == "__main__":
    unittest.main()

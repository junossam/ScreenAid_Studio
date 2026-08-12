from __future__ import annotations

import unittest

from live_zoom.transform import clamp, fullscreen_offset


class LiveZoomTransformTests(unittest.TestCase):
    MONITOR = (0, 0, 1920, 1080)

    def test_clamp_bounds(self) -> None:
        self.assertEqual(clamp(5, 0, 10), 5)
        self.assertEqual(clamp(-1, 0, 10), 0)
        self.assertEqual(clamp(11, 0, 10), 10)

    def test_unmagnified_offset_is_zero(self) -> None:
        offset = fullscreen_offset(960, 540, self.MONITOR, 1.0)
        self.assertEqual(offset, (0, 0))

    def test_offset_centers_anchor_at_default_scale(self) -> None:
        left, top, right, bottom = self.MONITOR
        center_x = (left + right) // 2
        center_y = (top + bottom) // 2
        x_offset, y_offset = fullscreen_offset(center_x, center_y, self.MONITOR, 2.0)
        self.assertEqual((x_offset, y_offset), (center_x // 2, center_y // 2))

    def test_offset_stays_within_monitor_bounds_at_edges(self) -> None:
        left, top, right, bottom = self.MONITOR
        for anchor_x, anchor_y in ((left, top), (right, bottom), (left, bottom), (right, top)):
            x_offset, y_offset = fullscreen_offset(anchor_x, anchor_y, self.MONITOR, 8.0)
            self.assertGreaterEqual(x_offset, left)
            self.assertLessEqual(x_offset, right)
            self.assertGreaterEqual(y_offset, top)
            self.assertLessEqual(y_offset, bottom)

    def test_offset_confined_to_second_monitor_with_negative_coordinates(self) -> None:
        second_monitor = (-1920, 0, 0, 1080)
        x_offset, y_offset = fullscreen_offset(-960, 540, second_monitor, 4.0)
        self.assertGreaterEqual(x_offset, second_monitor[0])
        self.assertLessEqual(x_offset, second_monitor[2])


if __name__ == "__main__":
    unittest.main()

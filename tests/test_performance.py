from __future__ import annotations

import unittest

from services.diagnostics.performance import PerformanceProbe, PerformanceRecord


class PerformanceProbeTests(unittest.TestCase):
    def test_disabled_probe_does_not_store_records(self) -> None:
        probe = PerformanceProbe(enabled=False)

        with probe.measure("capture", width=1920, secret="nope"):
            pass

        self.assertEqual(probe.records, [])

    def test_enabled_probe_keeps_only_safe_metadata(self) -> None:
        probe = PerformanceProbe(enabled=True)

        with probe.measure("capture", width=1920, height=1080, path="C:\\Users\\alice\\x.png"):
            pass

        self.assertEqual(len(probe.records), 1)
        self.assertEqual(probe.records[0].metadata, {"width": 1920, "height": 1080})

    def test_record_grade(self) -> None:
        self.assertEqual(PerformanceRecord("x", 10.0, {}).grade, "good")
        self.assertEqual(PerformanceRecord("x", 50.0, {}).grade, "watch")
        self.assertEqual(PerformanceRecord("x", 120.0, {}).grade, "slow")


if __name__ == "__main__":
    unittest.main()

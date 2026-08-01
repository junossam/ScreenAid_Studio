from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CaptureWorkerTests(unittest.TestCase):
    def test_capture_manager_uses_single_worker_thread(self) -> None:
        source = (ROOT / "capture" / "manager.py").read_text(encoding="utf-8")

        self.assertIn("class _CaptureWorker(QRunnable):", source)
        self.assertIn("self._thread_pool.setMaxThreadCount(1)", source)
        self.assertIn("self._capture_running", source)
        self.assertIn("GdiCaptureBackend().capture_region(self.request)", source)
        self.assertIn("Qt.ConnectionType.QueuedConnection", source)
        self.assertIn("self._thread_pool.start(worker)", source)
        self.assertNotIn("self.backend.capture_region(request)", source)


if __name__ == "__main__":
    unittest.main()

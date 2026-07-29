from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LiveViewWorkerTests(unittest.TestCase):
    def _source(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_live_view_uses_worker_thread(self) -> None:
        window = self._source("live_view/window.py")
        worker = self._source("live_view/worker.py")

        self.assertIn("QThread", window)
        self.assertIn("LiveCaptureWorker", window)
        self.assertIn("_ensure_worker", window)
        self.assertIn("_shutdown_worker", window)
        self.assertIn("Qt.ConnectionType.QueuedConnection", window)
        self.assertIn("moveToThread", window)
        self.assertIn("finished.connect(self._capture_finished)", window)
        self.assertIn("class LiveCaptureWorker", worker)
        self.assertIn("GdiCaptureBackend", worker)

    def test_live_view_keeps_only_one_pending_capture(self) -> None:
        window = self._source("live_view/window.py")

        self.assertIn("_pending_capture = False", window)
        self.assertIn("if self._capture_in_flight:", window)
        self.assertIn("self._pending_capture = True", window)
        self.assertNotIn("list[QImage]", window)
        self.assertNotIn("deque", window)


if __name__ == "__main__":
    unittest.main()

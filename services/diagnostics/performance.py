from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Iterator


@dataclass(frozen=True, slots=True)
class PerformanceRecord:
    operation: str
    duration_ms: float
    metadata: dict[str, Any]

    @property
    def grade(self) -> str:
        if self.duration_ms <= 16:
            return "good"
        if self.duration_ms <= 100:
            return "watch"
        return "slow"


class PerformanceProbe:
    def __init__(self, *, enabled: bool = False, slow_threshold_ms: float = 100.0) -> None:
        self.enabled = enabled
        self.slow_threshold_ms = slow_threshold_ms
        self.records: list[PerformanceRecord] = []

    @contextmanager
    def measure(self, operation: str, **metadata: Any) -> Iterator[None]:
        if not self.enabled:
            yield
            return

        started_at = perf_counter()
        try:
            yield
        finally:
            duration_ms = (perf_counter() - started_at) * 1000
            safe_metadata = self._safe_metadata(metadata)
            record = PerformanceRecord(operation, duration_ms, safe_metadata)
            self.records.append(record)

    @staticmethod
    def _safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "backend",
            "duration_ms",
            "fps_actual",
            "fps_target",
            "frames_dropped",
            "height",
            "operation",
            "width",
        }
        return {key: value for key, value in metadata.items() if key in allowed}

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import psutil


@dataclass
class ProcessMonitor:
    pid: int

    def __post_init__(self) -> None:
        self._process = psutil.Process(self.pid)
        # Prime psutil's non-blocking CPU measurement. The next call represents
        # CPU usage since this point rather than sleeping inside the supervisor.
        self._process.cpu_percent(interval=None)

    def sample(self) -> dict[str, Any]:
        try:
            processes = [self._process, *self._process.children(recursive=True)]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {"available": False}

        rss_bytes = 0
        child_count = 0
        for process in processes:
            try:
                rss_bytes += process.memory_info().rss
                if process.pid != self.pid:
                    child_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        try:
            cpu_percent = self._process.cpu_percent(interval=None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            cpu_percent = None

        return {
            "available": True,
            "cpu_percent": cpu_percent,
            "rss_bytes": rss_bytes,
            "child_processes": child_count,
        }

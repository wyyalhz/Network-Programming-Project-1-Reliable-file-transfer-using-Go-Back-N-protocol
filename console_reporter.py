from __future__ import annotations

import threading


class ConsoleReporter:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._lock = threading.Lock()

    def info(self, message: str) -> None:
        if not self.enabled:
            return
        with self._lock:
            try:
                print(message, flush=True)
            except OSError:
                self.enabled = False

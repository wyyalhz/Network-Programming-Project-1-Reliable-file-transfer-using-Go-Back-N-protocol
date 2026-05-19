from __future__ import annotations

import json
import threading
import time
from pathlib import Path


class EventLogger:
    def __init__(self, log_path: str | Path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def log(self, **fields: object) -> None:
        record = {
            "time": round(time.time(), 6),
            **fields,
        }
        with self._lock:
            with self.log_path.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(record, ensure_ascii=True) + "\n")

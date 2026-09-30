"""Event bus: every simulation event goes to an in-memory list, an events.jsonl file, and any live subscribers."""
from __future__ import annotations

import json
import queue
import threading
import time


class EventBus:
    def __init__(self, log_path: str | None = None):
        self.events: list[dict] = []
        self.subscribers: list[queue.Queue] = []
        self.lock = threading.Lock()
        self.log = open(log_path, "a", encoding="utf-8") if log_path else None
        self.t0 = time.time()

    def emit(self, type_: str, **payload) -> dict:
        ev = {"i": len(self.events), "t": round(time.time() - self.t0, 3), "type": type_, **payload}
        with self.lock:
            self.events.append(ev)
            if self.log:
                self.log.write(json.dumps(ev, ensure_ascii=False) + "\n")
                self.log.flush()
            subs = list(self.subscribers)
        for q in subs:
            q.put(ev)
        return ev

    def subscribe(self) -> tuple[list[dict], queue.Queue]:
        q: queue.Queue = queue.Queue()
        with self.lock:
            past = list(self.events)
            self.subscribers.append(q)
        return past, q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self.lock:
            if q in self.subscribers:
                self.subscribers.remove(q)

    def load(self, path: str) -> None:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    self.events.append(json.loads(line))

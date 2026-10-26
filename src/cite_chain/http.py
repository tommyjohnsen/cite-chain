# PROVENANCE (mirror of .provenance/ledger.jsonl; ledger wins)
# written-by: unknown (pre-provenance) | 2026-10-16 | f79efcb
# modified-by: codex/gpt-5.6-sol | 2026-10-26 | 00d4acd | provenance block added
# reviewed-by: claude-code/claude-opus-5-5 | 2026-10-26 | APPROVE_WITH_NITS
# reviewed-by: grok-build/grok-4.7 | 2026-10-26 | APPROVE_WITH_NITS
# END PROVENANCE
"""Shared stdlib HTTP, throttling, and local cache helpers."""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
from pathlib import Path
import threading
import time
from typing import Any
from urllib.request import Request, urlopen


class RateLimiter:
    def __init__(self, rate: float, *, clock: Callable[[], float] = time.monotonic,
                 sleeper: Callable[[float], None] = time.sleep) -> None:
        self.interval = 1.0 / rate
        self.clock = clock
        self.sleeper = sleeper
        self._next = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = self.clock()
            delay = self._next - now
            if delay > 0:
                self.sleeper(delay)
                now = self.clock()
            self._next = max(now, self._next) + self.interval


def get_json(url: str, *, headers: dict[str, str] | None = None,
             opener: Callable[..., Any] = urlopen, timeout: float = 30) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "cite-chain/0.1", **(headers or {})})
    with opener(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


class JsonCache:
    def __init__(self, directory: str | Path = ".cache/cite-chain") -> None:
        self.directory = Path(directory)

    def _path(self, namespace: str, key: str) -> Path:
        digest = hashlib.sha256(key.encode()).hexdigest()
        return self.directory / namespace / f"{digest}.json"

    def get(self, namespace: str, key: str) -> dict[str, Any] | None:
        path = self._path(namespace, key)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None

    def put(self, namespace: str, key: str, value: dict[str, Any]) -> None:
        path = self._path(namespace, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")

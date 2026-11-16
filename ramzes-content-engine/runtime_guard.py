"""Bounded, idempotent dispatch for Telegram webhook updates."""
from collections import OrderedDict
from threading import Lock
import time


class UpdateDispatcher:
    """Deduplicate Telegram retries and cap queued work during traffic bursts."""

    def __init__(self, max_pending=24, dedupe_ttl=21600, max_seen=10000, clock=None):
        self.max_pending = max(1, int(max_pending))
        self.dedupe_ttl = max(1, int(dedupe_ttl))
        self.max_seen = max(1, int(max_seen))
        self._clock = clock or time.monotonic
        self._lock = Lock()
        self._pending = 0
        self._seen = OrderedDict()

    @property
    def pending_count(self):
        with self._lock:
            return self._pending

    def _prune(self, now):
        while self._seen:
            _, created_at = next(iter(self._seen.items()))
            if now - created_at <= self.dedupe_ttl and len(self._seen) <= self.max_seen:
                break
            self._seen.popitem(last=False)

    def submit(self, executor, handler, update):
        update_id = update.get("update_id") if isinstance(update, dict) else None
        key = str(update_id) if update_id is not None else None
        now = self._clock()

        with self._lock:
            self._prune(now)
            if key is not None and key in self._seen:
                return "duplicate"
            if self._pending >= self.max_pending:
                return "full"
            if key is not None:
                self._seen[key] = now
                while len(self._seen) > self.max_seen:
                    self._seen.popitem(last=False)
            self._pending += 1

        try:
            future = executor.submit(handler, update)
        except Exception:
            with self._lock:
                self._pending = max(0, self._pending - 1)
                if key is not None:
                    self._seen.pop(key, None)
            raise

        future.add_done_callback(self._complete)
        return "queued"

    def _complete(self, _future):
        with self._lock:
            self._pending = max(0, self._pending - 1)

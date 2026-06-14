from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Callable, Iterable, TypeVar


T = TypeVar("T")


class RateLimiter:
    def __init__(self, max_per_second: int):
        self.interval = 1.0 / max(1, max_per_second)
        self._lock = Lock()
        self._last_call = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.time()
            sleep_for = self.interval - (now - self._last_call)
            if sleep_for > 0:
                time.sleep(sleep_for)
            self._last_call = time.time()


def fetch_many(
    items: Iterable[str],
    fetcher: Callable[[str], T],
    max_workers: int,
    max_per_second: int,
) -> dict[str, T]:
    limiter = RateLimiter(max_per_second)
    results: dict[str, T] = {}

    def wrapped(item: str) -> tuple[str, T]:
        limiter.wait()
        return item, fetcher(item)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(wrapped, item) for item in items]
        for future in as_completed(futures):
            key, value = future.result()
            results[key] = value
    return results

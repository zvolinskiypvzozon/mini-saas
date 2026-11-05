import os
import time
from collections import defaultdict, deque
from threading import Lock


class FailureLimiter:
    """Считает неудачные попытки по ключу в скользящем окне.

    Хранит состояние в памяти процесса: при нескольких экземплярах API
    счётчики нужно вынести в общее хранилище (Redis).
    """

    def __init__(self, max_failures: int, window_seconds: int):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def retry_after(self, key: str) -> int:
        """0 — можно пробовать, иначе через сколько секунд."""
        now = time.monotonic()
        with self._lock:
            attempts = self._failures[key]
            while attempts and attempts[0] <= now - self.window_seconds:
                attempts.popleft()
            if len(attempts) < self.max_failures:
                return 0
            return int(attempts[0] + self.window_seconds - now) + 1

    def failure(self, key: str) -> None:
        with self._lock:
            self._failures[key].append(time.monotonic())

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()


login_limiter = FailureLimiter(
    max_failures=int(os.environ.get("LOGIN_MAX_FAILURES", "5")),
    window_seconds=int(os.environ.get("LOGIN_WINDOW_SECONDS", "900")),
)

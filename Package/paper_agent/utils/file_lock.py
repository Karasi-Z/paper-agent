# -*- coding: utf-8 -*-

"""
File-based advisory lock helpers for project and resource coordination.
"""


import os
import time
from contextlib import AbstractContextManager
from pathlib import Path

import fcntl


class FileLock(AbstractContextManager):
    """
    Lightweight advisory lock backed by a lock file.
    """

    def __init__(self, path: str | Path, timeout_seconds: float = 10.0, poll_interval_seconds: float = 0.1) -> None:
        self.path = Path(path)
        self.timeout_seconds = max(0.1, timeout_seconds)
        self.poll_interval_seconds = max(0.05, poll_interval_seconds)
        self._file_obj = None

    def acquire(self) -> "FileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file_obj = self.path.open("a+", encoding="utf-8")
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                fcntl.flock(self._file_obj.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                self._file_obj.seek(0)
                self._file_obj.truncate()
                self._file_obj.write(str(os.getpid()))
                self._file_obj.flush()
                return self
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"Timed out waiting for lock: {self.path}")
                time.sleep(self.poll_interval_seconds)

    def release(self) -> None:
        if self._file_obj is None:
            return
        try:
            fcntl.flock(self._file_obj.fileno(), fcntl.LOCK_UN)
        finally:
            self._file_obj.close()
            self._file_obj = None

    def __enter__(self) -> "FileLock":
        return self.acquire()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()

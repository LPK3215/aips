from __future__ import annotations

from contextlib import contextmanager
from threading import BoundedSemaphore

from app.core.config import MAX_CONCURRENT_HEAVY_JOBS


class BusyError(RuntimeError):
    pass


_heavy_job_semaphore = BoundedSemaphore(MAX_CONCURRENT_HEAVY_JOBS)


@contextmanager
def heavy_job_slot():
    acquired = _heavy_job_semaphore.acquire(blocking=False)
    if not acquired:
        raise BusyError("服务器繁忙，请稍后再试。")
    try:
        yield
    finally:
        _heavy_job_semaphore.release()


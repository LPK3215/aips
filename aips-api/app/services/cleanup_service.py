from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from app.core.config import CLEANUP_INTERVAL_SECONDS, STORAGE_TTL_HOURS
from app.services.storage_service import storage_service
from app.services.task_service import task_service


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CleanupReport:
    cutoff_timestamp: float
    uploads_deleted: int
    results_deleted: int
    tasks_deleted: int
    temp_deleted: int


class CleanupService:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def cleanup_before(self, cutoff_timestamp: float) -> CleanupReport:
        uploads_deleted = storage_service.cleanup_uploads_before(cutoff_timestamp)
        linked_results_deleted, tasks_deleted = self._cleanup_expired_tasks_before(cutoff_timestamp)
        orphaned_results_deleted = self._cleanup_orphaned_results_before(cutoff_timestamp)
        temp_deleted = self._cleanup_stale_temp_files_before(cutoff_timestamp)
        return CleanupReport(
            cutoff_timestamp=cutoff_timestamp,
            uploads_deleted=uploads_deleted,
            results_deleted=linked_results_deleted + orphaned_results_deleted,
            tasks_deleted=tasks_deleted,
            temp_deleted=temp_deleted,
        )

    def run_once(self) -> CleanupReport:
        cutoff_timestamp = time.time() - STORAGE_TTL_HOURS * 3600
        return self.cleanup_before(cutoff_timestamp)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()

        # Run once at boot so storage doesn't grow indefinitely if the service restarts often.
        try:
            report = self.run_once()
            logger.info(
                "storage cleanup completed (uploads=%s results=%s tasks=%s temp=%s)",
                report.uploads_deleted,
                report.results_deleted,
                report.tasks_deleted,
                report.temp_deleted,
            )
        except Exception:  # pragma: no cover - best-effort cleanup
            logger.exception("storage cleanup failed on startup")

        self._thread = threading.Thread(
            target=self._worker,
            name="storage-cleanup",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout_seconds: float = 2.0) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout_seconds)

    def _worker(self) -> None:
        while not self._stop_event.wait(CLEANUP_INTERVAL_SECONDS):
            try:
                report = self.run_once()
                if report.uploads_deleted or report.results_deleted or report.tasks_deleted or report.temp_deleted:
                    logger.info(
                        "storage cleanup completed (uploads=%s results=%s tasks=%s temp=%s)",
                        report.uploads_deleted,
                        report.results_deleted,
                        report.tasks_deleted,
                        report.temp_deleted,
                    )
            except Exception:  # pragma: no cover - best-effort cleanup loop
                logger.exception("storage cleanup loop failed")

    def _cleanup_expired_tasks_before(self, cutoff_timestamp: float) -> tuple[int, int]:
        results_deleted = 0
        tasks_deleted = 0

        for path in task_service.tasks_dir.glob("*.json"):
            try:
                if path.stat().st_mtime >= cutoff_timestamp:
                    continue

                task = task_service.get_task(path.stem)
                if task is not None:
                    result_path = storage_service.get_result_path(path.stem, task.meta.format)
                    if result_path.exists():
                        result_path.unlink(missing_ok=True)
                        results_deleted += 1

                path.unlink(missing_ok=True)
                tasks_deleted += 1
            except OSError:
                continue

        return results_deleted, tasks_deleted

    def _cleanup_orphaned_results_before(self, cutoff_timestamp: float) -> int:
        deleted = 0
        for path in storage_service.results_dir.glob("*.*"):
            try:
                if path.stat().st_mtime >= cutoff_timestamp:
                    continue
                if task_service.get_task(path.stem) is not None:
                    continue
                path.unlink(missing_ok=True)
                deleted += 1
            except OSError:
                continue
        return deleted

    def _cleanup_stale_temp_files_before(self, cutoff_timestamp: float) -> int:
        deleted = 0
        for directory in (
            storage_service.uploads_dir,
            storage_service.results_dir,
            task_service.tasks_dir,
            storage_service.temp_dir,
        ):
            deleted += self._cleanup_temp_files_in_dir(directory, cutoff_timestamp)
        return deleted

    def _cleanup_temp_files_in_dir(self, directory: Path, cutoff_timestamp: float) -> int:
        deleted = 0
        for path in directory.glob("*.tmp"):
            try:
                if path.stat().st_mtime < cutoff_timestamp:
                    path.unlink(missing_ok=True)
                    deleted += 1
            except OSError:
                continue
        return deleted


cleanup_service = CleanupService()

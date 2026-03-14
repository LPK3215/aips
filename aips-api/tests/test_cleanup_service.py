import json
import os
import time
from pathlib import Path

from app.services.cleanup_service import cleanup_service
from app.services.storage_service import storage_service
from app.services.task_service import task_service


def _set_mtime(path: Path, timestamp: float) -> None:
    os.utime(path, (timestamp, timestamp))


def test_cleanup_service_removes_expired_tasks_orphaned_results_and_temps(
    monkeypatch,
    tmp_path: Path,
) -> None:
    uploads_dir = tmp_path / "uploads"
    results_dir = tmp_path / "results"
    tasks_dir = tmp_path / "tasks"
    temp_dir = tmp_path / "temp"
    uploads_dir.mkdir()
    results_dir.mkdir()
    tasks_dir.mkdir()
    temp_dir.mkdir()

    monkeypatch.setattr(storage_service, "uploads_dir", uploads_dir)
    monkeypatch.setattr(storage_service, "results_dir", results_dir)
    monkeypatch.setattr(storage_service, "temp_dir", temp_dir)
    monkeypatch.setattr(task_service, "tasks_dir", tasks_dir)

    old_timestamp = time.time() - 3600
    cutoff_timestamp = time.time() - 60

    task_id = "a" * 32
    linked_result = results_dir / f"{task_id}.jpg"
    linked_result.write_bytes(b"jpg-data")
    task_payload = {
        "task_id": task_id,
        "result_url": f"/api/v1/files/result/{task_id}",
        "download_url": f"/api/v1/files/download/{task_id}",
        "created_at": "2026-03-13T00:00:00+00:00",
        "meta": {
            "width_px": 413,
            "height_px": 626,
            "format": "jpg",
            "dpi": 300,
            "size_kb": 12.3,
            "filename": "demo.jpg",
            "background_color": "#ffffff",
            "preset_name": None,
        },
    }
    task_path = tasks_dir / f"{task_id}.json"
    task_path.write_text(json.dumps(task_payload), encoding="utf-8")

    orphan_result = results_dir / f"{'b' * 32}.png"
    orphan_result.write_bytes(b"png-data")

    stale_upload_tmp = uploads_dir / "upload.jpg.tmp"
    stale_upload_tmp.write_bytes(b"tmp")
    stale_task_tmp = tasks_dir / "task.json.tmp"
    stale_task_tmp.write_bytes(b"tmp")
    stale_archive_tmp = temp_dir / "archive.zip.tmp"
    stale_archive_tmp.write_bytes(b"tmp")

    for path in (linked_result, task_path, orphan_result, stale_upload_tmp, stale_task_tmp, stale_archive_tmp):
        _set_mtime(path, old_timestamp)

    report = cleanup_service.cleanup_before(cutoff_timestamp)

    assert report.uploads_deleted == 0
    assert report.tasks_deleted == 1
    assert report.results_deleted == 2
    assert report.temp_deleted == 3
    assert not linked_result.exists()
    assert not task_path.exists()
    assert not orphan_result.exists()
    assert not stale_upload_tmp.exists()
    assert not stale_task_tmp.exists()
    assert not stale_archive_tmp.exists()

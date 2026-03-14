import json
from pathlib import Path

from app.core.config import RESULTS_DIR, TASKS_DIR, ensure_storage_dirs
from app.schemas.tasks import TaskDetailResponse, TaskSummaryResponse
from app.services.image_service import ProcessedArtifact
from app.utils.ids import normalize_hex32


class TaskService:
    def __init__(self) -> None:
        ensure_storage_dirs()
        self.tasks_dir = TASKS_DIR
        self.results_dir = RESULTS_DIR

    def _task_path(self, task_id: str) -> Path:
        safe_id = normalize_hex32(task_id)
        return self.tasks_dir / f"{safe_id}.json"

    def _result_path(self, task_id: str, output_format: str) -> Path:
        safe_id = normalize_hex32(task_id)
        extension = ".jpg" if output_format == "jpg" else ".png"
        return self.results_dir / f"{safe_id}{extension}"

    def _load_task_payload(self, path: Path) -> dict | None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError):
            return None

    def _result_exists(self, task_id: str, output_format: str) -> bool:
        try:
            return self._result_path(task_id, output_format).exists()
        except ValueError:
            return False

    def save_task(self, artifact: ProcessedArtifact, params: dict | None = None) -> None:
        payload = artifact.to_task_response().model_dump(mode="json")
        if params is not None:
            payload["params"] = params
        target_path = self._task_path(artifact.task_id)
        tmp_path = target_path.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(target_path)

    def get_task(self, task_id: str) -> TaskDetailResponse | None:
        try:
            task_path = self._task_path(task_id)
        except ValueError:
            return None
        if not task_path.exists():
            return None

        payload = self._load_task_payload(task_path)
        if payload is None:
            return None

        output_format = str(payload.get("meta", {}).get("format", ""))
        payload["file_available"] = self._result_exists(task_path.stem, output_format)
        try:
            return TaskDetailResponse.model_validate(payload)
        except ValueError:
            return None

    def list_tasks(
        self,
        limit: int = 12,
        *,
        include_missing: bool = False,
    ) -> tuple[list[TaskSummaryResponse], int]:
        paths = sorted(
            self.tasks_dir.glob("*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        items: list[TaskSummaryResponse] = []
        missing_count = 0
        for path in paths:
            payload = self._load_task_payload(path)
            if payload is None:
                continue

            output_format = str(payload.get("meta", {}).get("format", ""))
            file_available = self._result_exists(path.stem, output_format)
            if not file_available:
                missing_count += 1

            if len(items) >= limit:
                continue

            if not include_missing and not file_available:
                continue

            try:
                payload["file_available"] = file_available
                items.append(TaskSummaryResponse.model_validate(payload))
            except ValueError:
                continue
        return items, missing_count

    def cleanup_tasks_before(self, cutoff_timestamp: float) -> int:
        deleted = 0
        for path in self.tasks_dir.glob("*.json"):
            try:
                if path.stat().st_mtime < cutoff_timestamp:
                    path.unlink(missing_ok=True)
                    deleted += 1
            except OSError:
                continue
        return deleted


task_service = TaskService()

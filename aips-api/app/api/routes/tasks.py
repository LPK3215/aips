from fastapi import APIRouter, HTTPException, Query

from app.schemas.tasks import TaskDetailResponse, TaskListResponse
from app.services.task_service import task_service


router = APIRouter()


@router.get("", response_model=TaskListResponse)
def list_tasks(
    limit: int = Query(default=12, ge=1, le=50),
    include_missing: bool = Query(default=False),
) -> TaskListResponse:
    items, missing_count = task_service.list_tasks(limit, include_missing=include_missing)
    return TaskListResponse(items=items, missing_count=missing_count)


@router.get("/{task_id}", response_model=TaskDetailResponse)
def get_task_detail(task_id: str) -> TaskDetailResponse:
    task = task_service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="处理任务不存在。")
    return task

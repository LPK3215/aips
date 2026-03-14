from fastapi import APIRouter, HTTPException, Query

from app.schemas.tasks import TaskDetailResponse, TaskListResponse, TaskStatusResponse
from app.services.task_service import task_service
from app.services.task_queue_service import task_queue_service


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


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str) -> TaskStatusResponse:
    # 首先检查任务队列中的状态
    queue_status = await task_queue_service.get_task_status(task_id)
    if queue_status:
        return TaskStatusResponse(
            task_id=task_id,
            status=queue_status.status,
            progress=queue_status.progress,
            message=queue_status.message,
        )
    
    # 然后检查是否已完成的任务
    task = task_service.get_task(task_id)
    if task:
        return TaskStatusResponse(
            task_id=task_id,
            status="completed",
            progress=100,
            message="任务已完成",
        )
    
    # 任务不存在
    raise HTTPException(status_code=404, detail="任务不存在。")

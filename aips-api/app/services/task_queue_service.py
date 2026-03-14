import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar

from app.core.config import ensure_storage_dirs
from app.services.image_service import ProcessedArtifact

logger = logging.getLogger("aips.queue")


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class QueueTask:
    task_id: str
    func: Callable[[], ProcessedArtifact]
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[ProcessedArtifact] = None
    error: Optional[str] = None
    progress: int = 0
    message: str = "任务排队中"


T = TypeVar('T')


class TaskQueueService:
    def __init__(self):
        ensure_storage_dirs()
        self.queue: asyncio.Queue[QueueTask] = asyncio.Queue()
        self.tasks: Dict[str, QueueTask] = {}
        self.worker_running = False
        self.worker_task: Optional[asyncio.Task] = None

    async def start_worker(self):
        if self.worker_running:
            return
        
        self.worker_running = True
        self.worker_task = asyncio.create_task(self._worker_loop())
        logger.info("Task queue worker started")

    async def stop_worker(self):
        if not self.worker_running:
            return
        
        self.worker_running = False
        if self.worker_task:
            await self.worker_task
        logger.info("Task queue worker stopped")

    async def _worker_loop(self):
        while self.worker_running:
            try:
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                await self._process_task(task)
                self.queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as exc:
                logger.exception("Worker loop error")

    async def _process_task(self, task: QueueTask):
        task.status = TaskStatus.PROCESSING
        task.progress = 50
        task.message = "任务处理中"
        logger.info(f"Processing task {task.task_id}")
        
        try:
            task.result = task.func()
            task.status = TaskStatus.COMPLETED
            task.progress = 100
            task.message = "任务已完成"
            logger.info(f"Task {task.task_id} completed successfully")
        except Exception as exc:
            task.error = str(exc)
            task.status = TaskStatus.FAILED
            task.message = task.error or "任务处理失败。"
            logger.error(f"Task {task.task_id} failed: {exc}")

    async def add_task(self, task_id: str, func: Callable[[], ProcessedArtifact]) -> QueueTask:
        if not self.worker_running:
            await self.start_worker()

        task = QueueTask(task_id=task_id, func=func)
        self.tasks[task_id] = task
        await self.queue.put(task)
        logger.info(f"Task {task_id} added to queue")
        return task

    async def get_task_status(self, task_id: str) -> Optional[QueueTask]:
        return self.tasks.get(task_id)

    def get_task(self, task_id: str) -> Optional[QueueTask]:
        return self.tasks.get(task_id)

    def remove_task(self, task_id: str):
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info(f"Task {task_id} removed from queue")


# Create a singleton instance
task_queue_service = TaskQueueService()

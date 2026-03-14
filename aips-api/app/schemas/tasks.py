from pydantic import BaseModel


class ImageInfo(BaseModel):
    width_px: int
    height_px: int
    format: str


class UploadResponse(BaseModel):
    file_id: str
    width_px: int
    height_px: int
    size_bytes: int
    format: str
    original_filename: str


class UploadBatchItem(BaseModel):
    index: int
    ok: bool
    upload: UploadResponse | None = None
    error: str | None = None


class UploadBatchResponse(BaseModel):
    items: list[UploadBatchItem]


class ResultMeta(BaseModel):
    width_px: int
    height_px: int
    format: str
    dpi: int
    size_kb: float
    filename: str
    background_color: str
    preset_name: str | None = None


class ProcessResponse(BaseModel):
    task_id: str
    result_url: str
    download_url: str
    meta: ResultMeta | None = None


class TaskDetailResponse(BaseModel):
    task_id: str
    result_url: str
    download_url: str
    file_available: bool = True
    meta: ResultMeta
    created_at: str
    params: dict | None = None


class TaskSummaryResponse(BaseModel):
    task_id: str
    result_url: str
    download_url: str
    file_available: bool = True
    meta: ResultMeta
    created_at: str


class TaskListResponse(BaseModel):
    items: list[TaskSummaryResponse]
    missing_count: int = 0


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int
    message: str

from __future__ import annotations

from pydantic import BaseModel, Field


class DownloadZipRequest(BaseModel):
    task_ids: list[str] = Field(min_length=1)
    filename: str | None = Field(default=None, max_length=120)
    include_manifest: bool = True


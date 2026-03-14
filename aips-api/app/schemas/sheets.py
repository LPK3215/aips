from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.images import CustomSize


class SheetOutputOptions(BaseModel):
    format: str = Field(default="jpg", pattern="^(jpg|png)$")
    dpi: int = Field(default=300, ge=72, le=600)
    quality: int = Field(default=92, ge=35, le=100)
    filename: str | None = Field(default=None, max_length=120)
    background_color: str = Field(default="#ffffff", pattern=r"^#([0-9a-fA-F]{6})$")


class ComposeSheetRequest(BaseModel):
    task_id: str
    page_size: CustomSize
    margin_mm: float = Field(default=6.0, ge=0.0, le=50.0)
    gap_mm: float = Field(default=4.0, ge=0.0, le=50.0)
    cols: int | None = Field(default=None, ge=1, le=20)
    rows: int | None = Field(default=None, ge=1, le=20)
    copies: int | None = Field(default=None, ge=1, le=400)
    show_cut_lines: bool = True
    cut_line_color: str = Field(default="#1b1b1b", pattern=r"^#([0-9a-fA-F]{6})$")
    cut_line_width: int = Field(default=2, ge=1, le=6)
    output: SheetOutputOptions = Field(default_factory=SheetOutputOptions)


from enum import Enum

from pydantic import BaseModel, Field, model_validator

from app.schemas.tasks import ResultMeta


class DimensionUnit(str, Enum):
    PX = "px"
    MM = "mm"
    CM = "cm"
    INCH = "inch"


class FitMode(str, Enum):
    FILL = "fill"
    FIT = "fit"


class CustomSize(BaseModel):
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    unit: DimensionUnit = DimensionUnit.PX
    dpi: int = Field(default=300, ge=72, le=600)


class RenderState(BaseModel):
    viewport_width: float = Field(gt=0)
    viewport_height: float = Field(gt=0)
    scale: float = Field(gt=0)
    offset_x: float = 0
    offset_y: float = 0
    fit_mode: FitMode = FitMode.FILL


class Adjustments(BaseModel):
    brightness: float = Field(default=0, ge=-100, le=100)
    contrast: float = Field(default=0, ge=-100, le=100)
    saturation: float = Field(default=0, ge=-100, le=100)
    sharpness: float = Field(default=0, ge=0, le=100)
    blur: float = Field(default=0, ge=0, le=20)


class OutputOptions(BaseModel):
    format: str = Field(default="jpg", pattern="^(jpg|png)$")
    dpi: int = Field(default=300, ge=72, le=600)
    quality: int = Field(default=90, ge=35, le=100)
    target_size_kb_min: int | None = Field(default=None, ge=1, le=10000)
    target_size_kb_max: int | None = Field(default=None, ge=1, le=10000)
    filename: str | None = Field(default=None, max_length=120)
    background_color: str = Field(default="#ffffff", pattern=r"^#([0-9a-fA-F]{6})$")
    replace_background: bool = False
    replace_feather: int = Field(default=6, ge=0, le=24)

    @model_validator(mode="after")
    def validate_size_range(self) -> "OutputOptions":
        if (
            self.target_size_kb_min is not None
            and self.target_size_kb_max is not None
            and self.target_size_kb_min > self.target_size_kb_max
        ):
            raise ValueError("target_size_kb_min 不能大于 target_size_kb_max")
        return self


class BasicOutputOptions(BaseModel):
    format: str = Field(default="jpg", pattern="^(jpg|png)$")
    dpi: int = Field(default=300, ge=72, le=600)
    quality: int = Field(default=90, ge=35, le=100)
    filename: str | None = Field(default=None, max_length=120)
    background_color: str = Field(default="#ffffff", pattern=r"^#([0-9a-fA-F]{6})$")


class ProcessRequest(BaseModel):
    file_id: str
    preset_id: str | None = None
    custom_size: CustomSize
    render: RenderState
    adjustments: Adjustments = Field(default_factory=Adjustments)
    output: OutputOptions = Field(default_factory=OutputOptions)


class FaceBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class SuggestRenderRequest(BaseModel):
    file_id: str
    custom_size: CustomSize
    viewport_width: float = Field(gt=0)
    viewport_height: float = Field(gt=0)
    fit_mode: FitMode = FitMode.FILL
    anchor_y: float = Field(default=0.42, ge=0.0, le=1.0)
    face_height_ratio: float = Field(default=0.55, ge=0.2, le=0.9)


class SuggestRenderResponse(BaseModel):
    render: RenderState
    face_box: FaceBox | None = None
    note: str


class BatchProcessRequest(BaseModel):
    items: list[ProcessRequest] = Field(min_length=1)


class BatchProcessItemResult(BaseModel):
    index: int
    ok: bool
    task_id: str | None = None
    result_url: str | None = None
    download_url: str | None = None
    meta: ResultMeta | None = None
    error: str | None = None


class BatchProcessResponse(BaseModel):
    items: list[BatchProcessItemResult]


class BatchAutoProcessRequest(BaseModel):
    file_ids: list[str] = Field(min_length=1)
    preset_id: str | None = None
    custom_size: CustomSize
    viewport_width: float = Field(gt=0)
    viewport_height: float = Field(gt=0)
    fit_mode: FitMode = FitMode.FILL
    anchor_y: float = Field(default=0.42, ge=0.0, le=1.0)
    face_height_ratio: float = Field(default=0.55, ge=0.2, le=0.9)
    adjustments: Adjustments = Field(default_factory=Adjustments)
    output: OutputOptions = Field(default_factory=OutputOptions)


class ResizeRequest(BaseModel):
    file_id: str
    width_px: int = Field(ge=1, le=12000)
    height_px: int = Field(ge=1, le=12000)
    output: BasicOutputOptions = Field(default_factory=BasicOutputOptions)


class EnhanceRequest(BaseModel):
    file_id: str
    scale_factor: float = Field(default=1.0, ge=1.0, le=3.0)
    denoise: int = Field(default=0, ge=0, le=30)
    sharpness: int = Field(default=24, ge=0, le=100)
    contrast: int = Field(default=8, ge=-30, le=50)
    auto_contrast: bool = True
    output: BasicOutputOptions = Field(default_factory=BasicOutputOptions)

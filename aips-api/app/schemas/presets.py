from pydantic import BaseModel, Field

from app.schemas.images import DimensionUnit


class PresetItem(BaseModel):
    id: str
    name: str
    category: str
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    unit: DimensionUnit
    dpi: int = Field(ge=72, le=600)
    format: str = Field(pattern="^(jpg|png)$")
    target_size_kb_min: int | None = None
    target_size_kb_max: int | None = None
    background_color: str = Field(pattern=r"^#([0-9a-fA-F]{6})$")
    description: str


class PresetCollectionResponse(BaseModel):
    items: list[PresetItem]
    categories: list[str]


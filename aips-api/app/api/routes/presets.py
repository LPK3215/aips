from fastapi import APIRouter

from app.schemas.presets import PresetCollectionResponse
from app.services.preset_service import preset_service


router = APIRouter()


@router.get("", response_model=PresetCollectionResponse)
def list_presets() -> PresetCollectionResponse:
    presets = preset_service.list_presets()
    categories = sorted({item.category for item in presets})
    return PresetCollectionResponse(items=presets, categories=categories)


import json
from functools import lru_cache

from app.core.config import PRESETS_FILE
from app.schemas.presets import PresetItem


class PresetService:
    @lru_cache(maxsize=1)
    def list_presets(self) -> list[PresetItem]:
        payload = json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
        return [PresetItem.model_validate(item) for item in payload]

    def get_preset(self, preset_id: str) -> PresetItem | None:
        for item in self.list_presets():
            if item.id == preset_id:
                return item
        return None


preset_service = PresetService()


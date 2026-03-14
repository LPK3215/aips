from fastapi import APIRouter

from app.api.routes import files, health, images, presets, tasks


api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(presets.router, prefix="/presets", tags=["presets"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(images.router, prefix="/images", tags=["images"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])


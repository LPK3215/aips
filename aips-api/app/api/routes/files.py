import json
import logging
import re
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.core.config import MAX_BATCH_ITEMS
from app.schemas.files import DownloadZipRequest
from app.schemas.tasks import UploadBatchItem, UploadBatchResponse, UploadResponse
from app.services.image_service import image_service
from app.services.storage_service import storage_service
from app.services.task_service import task_service


router = APIRouter()
logger = logging.getLogger("aips.audit")

_SAFE_ARCHIVE_NAME_RE = re.compile(r"[^a-zA-Z0-9_\-\u4e00-\u9fff]+")


def _sanitize_zip_name(value: str | None, fallback: str = "id-photo-batch") -> str:
    source = (value or fallback).strip()
    stem = Path(source).stem
    stem = _SAFE_ARCHIVE_NAME_RE.sub("-", stem).strip("-") or fallback
    return f"{stem}.zip"


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(request: Request, file: UploadFile = File(...)) -> UploadResponse:
    try:
        upload = await storage_service.save_upload_stream(file)
        image_info = image_service.inspect_image(upload.path)
    except HTTPException:
        if "upload" in locals():
            storage_service.delete_path(upload.path)
        raise
    except ValueError as exc:
        if "upload" in locals():
            storage_service.delete_path(upload.path)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive cleanup
        if "upload" in locals():
            storage_service.delete_path(upload.path)
        raise HTTPException(status_code=400, detail="上传文件不是有效图片。") from exc
    finally:
        await file.close()

    logger.info(
        "event=upload_completed request_id=%s file_id=%s original_filename=%s size_bytes=%s format=%s width_px=%s height_px=%s",
        _request_id(request),
        upload.file_id,
        file.filename or upload.path.name,
        upload.size_bytes,
        image_info.format,
        image_info.width_px,
        image_info.height_px,
    )

    return UploadResponse(
        file_id=upload.file_id,
        width_px=image_info.width_px,
        height_px=image_info.height_px,
        size_bytes=upload.size_bytes,
        format=image_info.format,
        original_filename=file.filename or upload.path.name,
    )


@router.post("/upload-batch", response_model=UploadBatchResponse, status_code=status.HTTP_201_CREATED)
async def upload_files(request: Request, files: list[UploadFile] = File(...)) -> UploadBatchResponse:
    if len(files) > MAX_BATCH_ITEMS:
        raise HTTPException(status_code=400, detail=f"批量上传最多支持 {MAX_BATCH_ITEMS} 张图片。")

    items: list[UploadBatchItem] = []
    for index, file in enumerate(files):
        upload = None
        try:
            upload = await storage_service.save_upload_stream(file)
            image_info = image_service.inspect_image(upload.path)
            items.append(
                UploadBatchItem(
                    index=index,
                    ok=True,
                    upload=UploadResponse(
                        file_id=upload.file_id,
                        width_px=image_info.width_px,
                        height_px=image_info.height_px,
                        size_bytes=upload.size_bytes,
                        format=image_info.format,
                        original_filename=file.filename or upload.path.name,
                    ),
                )
            )
        except HTTPException as exc:
            items.append(UploadBatchItem(index=index, ok=False, error=str(exc.detail)))
        except ValueError as exc:
            if upload is not None:
                storage_service.delete_path(upload.path)
            items.append(UploadBatchItem(index=index, ok=False, error=str(exc)))
        except Exception:
            if upload is not None:
                storage_service.delete_path(upload.path)
            items.append(UploadBatchItem(index=index, ok=False, error="上传文件不是有效图片。"))
        finally:
            await file.close()

    ok_count = sum(1 for item in items if item.ok)
    logger.info(
        "event=upload_batch_completed request_id=%s total=%s ok=%s failed=%s",
        _request_id(request),
        len(items),
        ok_count,
        len(items) - ok_count,
    )

    return UploadBatchResponse(items=items)


@router.get("/result/{task_id}")
def download_result(task_id: str) -> FileResponse:
    task = task_service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="处理结果不存在。")

    result_path = storage_service.get_result_path(task_id, task.meta.format)
    if not result_path.exists():
        raise HTTPException(status_code=410, detail="处理结果文件已过期被清理。")

    media_type = "image/jpeg" if task.meta.format == "jpg" else "image/png"
    return FileResponse(
        path=result_path,
        media_type=media_type,
        headers={"Content-Disposition": "inline"},
    )


@router.get("/download/{task_id}")
def download_attachment(task_id: str) -> FileResponse:
    task = task_service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="处理结果不存在。")

    result_path = storage_service.get_result_path(task_id, task.meta.format)
    if not result_path.exists():
        raise HTTPException(status_code=410, detail="处理结果文件已过期被清理。")

    media_type = "image/jpeg" if task.meta.format == "jpg" else "image/png"
    return FileResponse(
        path=result_path,
        media_type=media_type,
        filename=task.meta.filename,
    )


@router.post("/download-zip")
def download_zip(request: Request, payload: DownloadZipRequest) -> FileResponse:
    if len(payload.task_ids) > MAX_BATCH_ITEMS:
        raise HTTPException(status_code=400, detail=f"最多支持 {MAX_BATCH_ITEMS} 个任务打包下载。")

    missing: list[str] = []
    missing_files: list[str] = []
    entries: list[dict] = []
    used_names: set[str] = set()
    archive_path = storage_service.create_temp_archive_path()

    try:
        with zipfile.ZipFile(archive_path, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for task_id in payload.task_ids:
                task = task_service.get_task(task_id)
                if task is None:
                    missing.append(task_id)
                    continue

                result_path = storage_service.get_result_path(task_id, task.meta.format)
                if not result_path.exists():
                    missing_files.append(task_id)
                    continue

                original_name = task.meta.filename or f"{task_id}.{task.meta.format}"
                arcname = original_name
                base, ext = Path(original_name).stem, Path(original_name).suffix
                counter = 2
                while arcname in used_names:
                    arcname = f"{base}-{counter:02d}{ext}"
                    counter += 1
                used_names.add(arcname)

                archive.write(result_path, arcname=arcname)

                if payload.include_manifest:
                    entries.append(
                        {
                            "task_id": task.task_id,
                            "filename": arcname,
                            "meta": task.meta.model_dump(mode="json"),
                            "created_at": task.created_at,
                            "params": task.params,
                        }
                    )

            if payload.include_manifest:
                archive.writestr(
                    "manifest.json",
                    json.dumps(
                        {
                            "items": entries,
                            "missing": missing,
                            "missing_files": missing_files,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ).encode("utf-8"),
                )

        if not entries and not used_names:
            raise HTTPException(status_code=404, detail="没有可打包的任务结果（可能已过期被清理）。")
    except HTTPException:
        storage_service.delete_path(archive_path)
        raise
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        storage_service.delete_path(archive_path)
        raise HTTPException(status_code=500, detail="打包下载失败，请稍后重试。") from exc

    zip_name = _sanitize_zip_name(payload.filename)
    archive_size = archive_path.stat().st_size
    logger.info(
        "event=download_zip_completed request_id=%s requested=%s exported=%s missing=%s missing_files=%s bytes=%s",
        _request_id(request),
        len(payload.task_ids),
        len(used_names),
        len(missing),
        len(missing_files),
        archive_size,
    )
    return FileResponse(
        path=archive_path,
        media_type="application/zip",
        filename=zip_name,
        background=BackgroundTask(storage_service.delete_path, archive_path),
    )

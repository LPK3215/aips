import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.core.config import MAX_BATCH_ITEMS
from app.core.limits import BusyError, heavy_job_slot
from app.schemas.sheets import ComposeSheetRequest
from app.schemas.images import (
    BatchAutoProcessRequest,
    BatchProcessItemResult,
    BatchProcessRequest,
    BatchProcessResponse,
    EnhanceRequest,
    ProcessRequest,
    ResizeRequest,
    SuggestRenderRequest,
    SuggestRenderResponse,
)
from app.schemas.tasks import ProcessResponse
from app.services.face_service import face_service
from app.services.image_service import image_service
from app.services.preset_service import preset_service
from app.services.storage_service import storage_service
from app.services.task_service import task_service


router = APIRouter()
logger = logging.getLogger("aips.audit")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def _save_task_or_cleanup(artifact, params: dict) -> None:
    try:
        task_service.save_task(artifact, params=params)
    except Exception as exc:  # pragma: no cover - defensive cleanup
        storage_service.delete_path(artifact.output_path)
        raise HTTPException(
            status_code=500,
            detail="处理结果保存失败，请稍后重试。",
        ) from exc


@router.post("/process", response_model=ProcessResponse, status_code=status.HTTP_201_CREATED)
def process_image(request: Request, payload: ProcessRequest) -> ProcessResponse:
    upload_path = storage_service.get_upload_path(payload.file_id)
    if upload_path is None:
        raise HTTPException(status_code=404, detail="原始图片不存在，请重新上传。")

    preset = None
    if payload.preset_id:
        preset = preset_service.get_preset(payload.preset_id)
        if preset is None:
            raise HTTPException(status_code=404, detail="所选规格模板不存在。")

    try:
        with heavy_job_slot():
            artifact = image_service.process_image(
                source_path=upload_path,
                request=payload,
                output_dir=storage_service.results_dir,
                preset_name=preset.name if preset else None,
            )
    except BusyError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _save_task_or_cleanup(artifact, params=payload.model_dump(mode="json"))
    logger.info(
        "event=process_completed request_id=%s file_id=%s task_id=%s preset_id=%s width_px=%s height_px=%s format=%s size_kb=%s",
        _request_id(request),
        payload.file_id,
        artifact.task_id,
        payload.preset_id or "",
        artifact.meta.width_px,
        artifact.meta.height_px,
        artifact.meta.format,
        artifact.meta.size_kb,
    )

    return ProcessResponse(
        task_id=artifact.task_id,
        result_url=f"/api/v1/files/result/{artifact.task_id}",
        download_url=f"/api/v1/files/download/{artifact.task_id}",
        meta=artifact.meta,
    )


@router.post("/resize", response_model=ProcessResponse, status_code=status.HTTP_201_CREATED)
def resize_image(request: Request, payload: ResizeRequest) -> ProcessResponse:
    upload_path = storage_service.get_upload_path(payload.file_id)
    if upload_path is None:
        raise HTTPException(status_code=404, detail="原始图片不存在，请重新上传。")

    try:
        with heavy_job_slot():
            artifact = image_service.resize_image(
                source_path=upload_path,
                request=payload,
                output_dir=storage_service.results_dir,
                preset_name="图片缩放",
            )
    except BusyError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _save_task_or_cleanup(artifact, params=payload.model_dump(mode="json"))
    logger.info(
        "event=resize_completed request_id=%s file_id=%s task_id=%s width_px=%s height_px=%s format=%s size_kb=%s",
        _request_id(request),
        payload.file_id,
        artifact.task_id,
        artifact.meta.width_px,
        artifact.meta.height_px,
        artifact.meta.format,
        artifact.meta.size_kb,
    )
    return ProcessResponse(
        task_id=artifact.task_id,
        result_url=f"/api/v1/files/result/{artifact.task_id}",
        download_url=f"/api/v1/files/download/{artifact.task_id}",
        meta=artifact.meta,
    )


@router.post("/enhance", response_model=ProcessResponse, status_code=status.HTTP_201_CREATED)
def enhance_image(request: Request, payload: EnhanceRequest) -> ProcessResponse:
    upload_path = storage_service.get_upload_path(payload.file_id)
    if upload_path is None:
        raise HTTPException(status_code=404, detail="原始图片不存在，请重新上传。")

    try:
        with heavy_job_slot():
            artifact = image_service.enhance_image(
                source_path=upload_path,
                request=payload,
                output_dir=storage_service.results_dir,
                preset_name="清晰增强",
            )
    except BusyError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _save_task_or_cleanup(artifact, params=payload.model_dump(mode="json"))
    logger.info(
        "event=enhance_completed request_id=%s file_id=%s task_id=%s scale_factor=%s denoise=%s sharpness=%s format=%s size_kb=%s",
        _request_id(request),
        payload.file_id,
        artifact.task_id,
        payload.scale_factor,
        payload.denoise,
        payload.sharpness,
        artifact.meta.format,
        artifact.meta.size_kb,
    )
    return ProcessResponse(
        task_id=artifact.task_id,
        result_url=f"/api/v1/files/result/{artifact.task_id}",
        download_url=f"/api/v1/files/download/{artifact.task_id}",
        meta=artifact.meta,
    )


@router.post("/suggest-render", response_model=SuggestRenderResponse)
def suggest_render(request: Request, payload: SuggestRenderRequest) -> SuggestRenderResponse:
    upload_path = storage_service.get_upload_path(payload.file_id)
    if upload_path is None:
        raise HTTPException(status_code=404, detail="原始图片不存在，请重新上传。")

    try:
        with heavy_job_slot():
            render, face = image_service.suggest_render(upload_path, payload)
    except BusyError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if face is None:
        logger.info(
            "event=suggest_render_completed request_id=%s file_id=%s face_detected=false fit_mode=%s viewport=%sx%s",
            _request_id(request),
            payload.file_id,
            payload.fit_mode,
            payload.viewport_width,
            payload.viewport_height,
        )
        return SuggestRenderResponse(
            render=render,
            face_box=None,
            note=(
                "当前环境未启用人脸检测，已按居中构图给出建议。"
                if not face_service.available
                else "未检测到人脸，已按居中构图给出建议。"
            ),
        )

    logger.info(
        "event=suggest_render_completed request_id=%s file_id=%s face_detected=true fit_mode=%s viewport=%sx%s",
        _request_id(request),
        payload.file_id,
        payload.fit_mode,
        payload.viewport_width,
        payload.viewport_height,
    )
    return SuggestRenderResponse(
        render=render,
        face_box={"x": face.x, "y": face.y, "width": face.width, "height": face.height},
        note="已基于人脸检测给出自动居中建议。",
    )


@router.post("/process-batch", response_model=BatchProcessResponse)
def process_batch(request: Request, payload: BatchProcessRequest) -> BatchProcessResponse:
    if len(payload.items) > MAX_BATCH_ITEMS:
        raise HTTPException(status_code=400, detail=f"批量处理最多支持 {MAX_BATCH_ITEMS} 张图片。")

    items: list[BatchProcessItemResult] = []

    try:
        with heavy_job_slot():
            for index, item in enumerate(payload.items):
                artifact = None
                upload_path = storage_service.get_upload_path(item.file_id)
                if upload_path is None:
                    items.append(
                        BatchProcessItemResult(
                            index=index,
                            ok=False,
                            error="原始图片不存在，请重新上传。",
                        )
                    )
                    continue

                preset = None
                if item.preset_id:
                    preset = preset_service.get_preset(item.preset_id)
                    if preset is None:
                        items.append(
                            BatchProcessItemResult(
                                index=index,
                                ok=False,
                                error="所选规格模板不存在。",
                            )
                        )
                        continue

                try:
                    artifact = image_service.process_image(
                        source_path=upload_path,
                        request=item,
                        output_dir=storage_service.results_dir,
                        preset_name=preset.name if preset else None,
                    )
                    task_service.save_task(artifact, params=item.model_dump(mode="json"))
                except ValueError as exc:
                    items.append(
                        BatchProcessItemResult(
                            index=index,
                            ok=False,
                            error=str(exc),
                        )
                    )
                    continue
                except Exception as exc:  # pragma: no cover - defensive cleanup
                    if artifact is not None:
                        storage_service.delete_path(artifact.output_path)
                    items.append(
                        BatchProcessItemResult(
                            index=index,
                            ok=False,
                            error="处理失败。",
                        )
                    )
                    continue

                items.append(
                    BatchProcessItemResult(
                        index=index,
                        ok=True,
                        task_id=artifact.task_id,
                        result_url=f"/api/v1/files/result/{artifact.task_id}",
                        download_url=f"/api/v1/files/download/{artifact.task_id}",
                        meta=artifact.meta,
                    )
                )
    except BusyError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    ok_count = sum(1 for item in items if item.ok)
    logger.info(
        "event=process_batch_completed request_id=%s total=%s ok=%s failed=%s",
        _request_id(request),
        len(items),
        ok_count,
        len(items) - ok_count,
    )
    return BatchProcessResponse(items=items)


@router.post("/process-batch-auto", response_model=BatchProcessResponse)
def process_batch_auto(request: Request, payload: BatchAutoProcessRequest) -> BatchProcessResponse:
    if len(payload.file_ids) > MAX_BATCH_ITEMS:
        raise HTTPException(status_code=400, detail=f"批量处理最多支持 {MAX_BATCH_ITEMS} 张图片。")

    preset = None
    if payload.preset_id:
        preset = preset_service.get_preset(payload.preset_id)
        if preset is None:
            raise HTTPException(status_code=404, detail="所选规格模板不存在。")

    items: list[BatchProcessItemResult] = []

    try:
        with heavy_job_slot():
            for index, file_id in enumerate(payload.file_ids):
                artifact = None
                upload_path = storage_service.get_upload_path(file_id)
                if upload_path is None:
                    items.append(
                        BatchProcessItemResult(
                            index=index,
                            ok=False,
                            error="原始图片不存在，请重新上传。",
                        )
                    )
                    continue

                try:
                    render, _face = image_service.suggest_render(
                        upload_path,
                        SuggestRenderRequest(
                            file_id=file_id,
                            custom_size=payload.custom_size,
                            viewport_width=payload.viewport_width,
                            viewport_height=payload.viewport_height,
                            fit_mode=payload.fit_mode,
                            anchor_y=payload.anchor_y,
                            face_height_ratio=payload.face_height_ratio,
                        ),
                    )

                    output = payload.output.model_copy(deep=True)
                    if output.filename:
                        output.filename = f"{output.filename}-{index + 1:02d}"

                    process_request = ProcessRequest(
                        file_id=file_id,
                        preset_id=payload.preset_id,
                        custom_size=payload.custom_size,
                        render=render,
                        adjustments=payload.adjustments,
                        output=output,
                    )

                    artifact = image_service.process_image(
                        source_path=upload_path,
                        request=process_request,
                        output_dir=storage_service.results_dir,
                        preset_name=preset.name if preset else None,
                    )
                    task_service.save_task(artifact, params=process_request.model_dump(mode="json"))
                except ValueError as exc:
                    items.append(
                        BatchProcessItemResult(
                            index=index,
                            ok=False,
                            error=str(exc),
                        )
                    )
                    continue
                except Exception as exc:  # pragma: no cover - defensive cleanup
                    if artifact is not None:
                        storage_service.delete_path(artifact.output_path)
                    items.append(
                        BatchProcessItemResult(
                            index=index,
                            ok=False,
                            error="处理失败。",
                        )
                    )
                    continue

                items.append(
                    BatchProcessItemResult(
                        index=index,
                        ok=True,
                        task_id=artifact.task_id,
                        result_url=f"/api/v1/files/result/{artifact.task_id}",
                        download_url=f"/api/v1/files/download/{artifact.task_id}",
                        meta=artifact.meta,
                    )
                )
    except BusyError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    ok_count = sum(1 for item in items if item.ok)
    logger.info(
        "event=process_batch_auto_completed request_id=%s total=%s ok=%s failed=%s preset_id=%s",
        _request_id(request),
        len(items),
        ok_count,
        len(items) - ok_count,
        payload.preset_id or "",
    )
    return BatchProcessResponse(items=items)


@router.post("/compose-sheet", response_model=ProcessResponse, status_code=status.HTTP_201_CREATED)
def compose_sheet(request: Request, payload: ComposeSheetRequest) -> ProcessResponse:
    source_task = task_service.get_task(payload.task_id)
    if source_task is None:
        raise HTTPException(status_code=404, detail="原始处理结果不存在。")

    source_path = storage_service.get_result_path(payload.task_id, source_task.meta.format)
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="原始处理结果文件不存在（可能已过期被清理）。")

    try:
        with heavy_job_slot():
            output = payload.output.model_copy(deep=True)
            output.dpi = payload.page_size.dpi
            artifact = image_service.compose_sheet(
                source_path=source_path,
                page_size=payload.page_size,
                margin_mm=payload.margin_mm,
                gap_mm=payload.gap_mm,
                cols=payload.cols,
                rows=payload.rows,
                copies=payload.copies,
                show_cut_lines=payload.show_cut_lines,
                cut_line_color=payload.cut_line_color,
                cut_line_width=payload.cut_line_width,
                output=output,
                output_dir=storage_service.results_dir,
                preset_name="打印排版",
            )
    except BusyError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _save_task_or_cleanup(artifact, params=payload.model_dump(mode="json"))
    logger.info(
        "event=compose_sheet_completed request_id=%s source_task_id=%s task_id=%s width_px=%s height_px=%s format=%s",
        _request_id(request),
        payload.task_id,
        artifact.task_id,
        artifact.meta.width_px,
        artifact.meta.height_px,
        artifact.meta.format,
    )

    return ProcessResponse(
        task_id=artifact.task_id,
        result_url=f"/api/v1/files/result/{artifact.task_id}",
        download_url=f"/api/v1/files/download/{artifact.task_id}",
        meta=artifact.meta,
    )

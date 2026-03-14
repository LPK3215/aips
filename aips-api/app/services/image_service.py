from __future__ import annotations

import hashlib
import io
import math
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

try:
    import cv2
except ImportError:  # pragma: no cover - depends on runtime environment
    cv2 = None

from app.core.config import MAX_IMAGE_PIXELS, UPLOADS_DIR
from app.schemas.images import (
    Adjustments,
    BasicOutputOptions,
    EnhanceRequest,
    FitMode,
    OutputOptions,
    ProcessRequest,
    RenderState,
    ResizeRequest,
    SuggestRenderRequest,
)
from app.schemas.tasks import ImageInfo, ResultMeta, TaskDetailResponse
from app.services.face_service import FaceBox, face_service
from app.utils.image_math import resolve_output_size

# 缓存目录
CACHE_DIR = UPLOADS_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# 缓存过期时间（秒）
CACHE_EXPIRY = 24 * 60 * 60  # 24小时


def _generate_cache_key(source_path: Path, params: dict) -> str:
    """生成缓存键，基于源文件路径和处理参数"""
    # 计算源文件的哈希值
    with open(source_path, 'rb') as f:
        file_hash = hashlib.md5(f.read()).hexdigest()
    
    # 计算参数的哈希值
    params_str = str(sorted(params.items())).encode('utf-8')
    params_hash = hashlib.md5(params_str).hexdigest()
    
    # 组合哈希值生成缓存键
    return f"{file_hash}_{params_hash}"

def _get_cache_path(cache_key: str, extension: str) -> Path:
    """获取缓存文件路径"""
    return CACHE_DIR / f"{cache_key}.{extension}"

def _is_cache_valid(cache_path: Path) -> bool:
    """检查缓存是否有效（存在且未过期）"""
    if not cache_path.exists():
        return False
    
    # 检查缓存是否过期
    mtime = cache_path.stat().st_mtime
    current_time = time.time()
    return current_time - mtime < CACHE_EXPIRY

def _cleanup_expired_cache():
    """清理过期的缓存文件"""
    current_time = time.time()
    for cache_file in CACHE_DIR.glob("*.*"):
        mtime = cache_file.stat().st_mtime
        if current_time - mtime >= CACHE_EXPIRY:
            try:
                cache_file.unlink()
            except Exception:
                pass


Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


def _mm_to_px(value_mm: float, dpi: int) -> int:
    return max(0, int(round((value_mm / 25.4) * dpi)))


def _draw_cut_marks(
    canvas: Image.Image,
    x: int,
    y: int,
    width: int,
    height: int,
    color: str,
    line_width: int,
) -> None:
    draw = ImageDraw.Draw(canvas)
    rgba = _hex_to_rgba(color)
    mark_len = max(10, min(40, int(round(min(width, height) * 0.08))))

    left = x
    top = y
    right = x + width
    bottom = y + height

    # Top-left
    draw.line([(left, top), (left + mark_len, top)], fill=rgba, width=line_width)
    draw.line([(left, top), (left, top + mark_len)], fill=rgba, width=line_width)
    # Top-right
    draw.line([(right - mark_len, top), (right, top)], fill=rgba, width=line_width)
    draw.line([(right, top), (right, top + mark_len)], fill=rgba, width=line_width)
    # Bottom-left
    draw.line([(left, bottom), (left + mark_len, bottom)], fill=rgba, width=line_width)
    draw.line([(left, bottom - mark_len), (left, bottom)], fill=rgba, width=line_width)
    # Bottom-right
    draw.line([(right - mark_len, bottom), (right, bottom)], fill=rgba, width=line_width)
    draw.line([(right, bottom - mark_len), (right, bottom)], fill=rgba, width=line_width)


def _hex_to_rgba(value: str) -> tuple[int, int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4)) + (255,)


def _sanitize_filename(value: str | None, fallback: str, output_format: str) -> str:
    source = (value or fallback).strip()
    source = Path(source).stem
    source = re.sub(r"[^a-zA-Z0-9_\-\u4e00-\u9fff]+", "-", source).strip("-")
    source = source or fallback
    extension = ".jpg" if output_format == "jpg" else ".png"
    return f"{source}{extension}"


def _encode_rgb_jpeg(image: Image.Image, dpi: int, quality: int) -> bytes:
    buffer = io.BytesIO()
    image.save(
        buffer,
        format="JPEG",
        quality=quality,
        optimize=True,
        subsampling=0,
        dpi=(dpi, dpi),
    )
    return buffer.getvalue()


def _choose_best_bytes(
    candidates: list[tuple[bytes, float]],
    target_min: int | None,
    target_max: int | None,
) -> bytes:
    if not candidates:
        raise ValueError("没有可用的压缩候选。")

    if target_min is None and target_max is None:
        return candidates[-1][0]

    def score(size_kb: float) -> float:
        if target_min is not None and size_kb < target_min:
            return target_min - size_kb
        if target_max is not None and size_kb > target_max:
            return size_kb - target_max
        return 0

    best_data, _ = min(candidates, key=lambda item: score(item[1]))
    return best_data


def _compress_jpeg_to_target(image: Image.Image, output: OutputOptions) -> bytes:
    if output.target_size_kb_min is None and output.target_size_kb_max is None:
        return _encode_rgb_jpeg(image, output.dpi, output.quality)

    low = 35
    high = max(low, output.quality)
    candidates: list[tuple[bytes, float]] = []

    attempts = 0
    while low <= high and attempts < 8:
        quality = (low + high) // 2
        attempts += 1
        data = _encode_rgb_jpeg(image, output.dpi, quality)
        size_kb = len(data) / 1024
        candidates.append((data, size_kb))

        if output.target_size_kb_min is not None and size_kb < output.target_size_kb_min:
            low = quality + 1
            continue

        if output.target_size_kb_max is not None and size_kb > output.target_size_kb_max:
            high = quality - 1
            continue

        return data

    return _choose_best_bytes(candidates, output.target_size_kb_min, output.target_size_kb_max)


def _apply_adjustments(image: Image.Image, adjustments: Adjustments) -> Image.Image:
    alpha = image.getchannel("A") if "A" in image.getbands() else None
    working = image.convert("RGB")

    if adjustments.brightness:
        factor = max(0.0, 1 + adjustments.brightness / 100)
        working = ImageEnhance.Brightness(working).enhance(factor)

    if adjustments.contrast:
        factor = max(0.0, 1 + adjustments.contrast / 100)
        working = ImageEnhance.Contrast(working).enhance(factor)

    if adjustments.saturation:
        factor = max(0.0, 1 + adjustments.saturation / 100)
        working = ImageEnhance.Color(working).enhance(factor)

    if adjustments.sharpness:
        percent = 100 + int(adjustments.sharpness * 4)
        working = working.filter(
            ImageFilter.UnsharpMask(radius=1.6, percent=percent, threshold=3)
        )

    if adjustments.blur:
        if cv2 is not None:
            array = np.array(working)
            kernel = max(3, int(math.ceil(adjustments.blur) * 2 + 1))
            array = cv2.GaussianBlur(array, (kernel, kernel), 0)
            working = Image.fromarray(array)
        else:
            working = working.filter(ImageFilter.GaussianBlur(radius=float(adjustments.blur)))

    if alpha is None:
        return working.convert("RGBA")

    merged = working.convert("RGBA")
    merged.putalpha(alpha)
    return merged


def _render_viewport(
    source: Image.Image,
    render: RenderState,
    target_width: int,
    target_height: int,
    background_color: str,
) -> Image.Image:
    scale_ratio = target_width / render.viewport_width
    canvas = Image.new("RGBA", (target_width, target_height), _hex_to_rgba(background_color))

    displayed_width = source.width * render.scale
    displayed_height = source.height * render.scale
    resized_width = max(1, round(displayed_width * scale_ratio))
    resized_height = max(1, round(displayed_height * scale_ratio))

    image_left = render.viewport_width / 2 + render.offset_x - displayed_width / 2
    image_top = render.viewport_height / 2 + render.offset_y - displayed_height / 2

    paste_x = round(image_left * scale_ratio)
    paste_y = round(image_top * scale_ratio)

    rendered = source.resize((resized_width, resized_height), Image.Resampling.LANCZOS)
    canvas.paste(rendered, (paste_x, paste_y), rendered)
    return canvas


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _replace_background_simple(
    image: Image.Image,
    background_color: str,
    feather: int,
) -> Image.Image:
    # Fallback matte estimation for simple studio-like backgrounds when OpenCV is unavailable.
    rgba = image.convert("RGBA")
    array = np.asarray(rgba, dtype=np.uint8)
    rgb = array[..., :3].astype(np.float32)
    height, width = rgb.shape[:2]
    if width < 2 or height < 2:
        return rgba

    patch = max(4, min(24, min(width, height) // 12 or 4))
    corners = np.concatenate(
        [
            rgb[:patch, :patch].reshape(-1, 3),
            rgb[:patch, -patch:].reshape(-1, 3),
            rgb[-patch:, :patch].reshape(-1, 3),
            rgb[-patch:, -patch:].reshape(-1, 3),
        ],
        axis=0,
    )
    border = np.concatenate(
        [
            rgb[0, :, :].reshape(-1, 3),
            rgb[-1, :, :].reshape(-1, 3),
            rgb[:, 0, :].reshape(-1, 3),
            rgb[:, -1, :].reshape(-1, 3),
        ],
        axis=0,
    )

    estimated_bg = corners.mean(axis=0)
    border_distance = np.linalg.norm(border - estimated_bg, axis=1)
    threshold = float(np.percentile(border_distance, 90) + 18.0)
    threshold = _clamp(threshold, 18.0, 72.0)

    distance = np.linalg.norm(rgb - estimated_bg, axis=2)
    keep_mask = Image.fromarray(np.where(distance > threshold, 255, 0).astype(np.uint8))
    if feather > 0:
        keep_mask = keep_mask.filter(ImageFilter.GaussianBlur(radius=max(0.5, feather * 0.6)))

    keep = np.asarray(keep_mask, dtype=np.float32) / 255.0
    bg_rgb = np.array(_hex_to_rgba(background_color)[:3], dtype=np.float32)
    composed = rgb * keep[..., None] + bg_rgb * (1.0 - keep[..., None])
    result = np.dstack(
        (
            np.clip(composed, 0, 255).astype(np.uint8),
            np.full((height, width), 255, dtype=np.uint8),
        )
    )
    return Image.fromarray(result)


def _replace_background_grabcut(
    image: Image.Image,
    background_color: str,
    feather: int,
    background_image: Image.Image | None = None,
) -> Image.Image:
    if cv2 is None:
        return _replace_background_simple(image, background_color, feather)

    # 快速检查图像大小，避免大图像处理时间过长
    width, height = image.size
    face = None
    
    # 只在需要时创建RGB数组
    if width * height <= 10000000:  # 10MP以下直接处理
        rgb = np.array(image.convert("RGB"))
        face = face_service.detect_largest_face(rgb)
    else:
        # 对大图像进行降采样处理
        scale_factor = min(1.0, math.sqrt(10000000 / (width * height)))
        new_width = max(640, int(width * scale_factor))
        new_height = max(480, int(height * scale_factor))
        small_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        small_rgb = np.array(small_image.convert("RGB"))
        face = face_service.detect_largest_face(small_rgb)
        if face:
            # 将检测结果映射回原始图像
            face.x = int(face.x / scale_factor)
            face.y = int(face.y / scale_factor)
            face.width = int(face.width / scale_factor)
            face.height = int(face.height / scale_factor)

    if face:
        rect = (
            int(_clamp(face.x - face.width * 1.2, 0, width - 2)),
            int(_clamp(face.y - face.height * 1.3, 0, height - 2)),
            int(_clamp(face.width * 3.4, 2, width - 1)),
            int(_clamp(face.height * 4.4, 2, height - 1)),
        )
    else:
        margin_x = int(width * 0.12)
        margin_y = int(height * 0.08)
        rect = (margin_x, margin_y, width - margin_x * 2, height - margin_y * 2)

    # 对于大图像，使用分块处理以减少内存使用
    if width * height > 15000000:  # 15MP
        return _process_large_image_in_chunks(
            image, background_color, feather, background_image, rect
        )

    # 对于中等大小的图像，使用常规处理
    if 'rgb' not in locals():
        rgb = np.array(image.convert("RGB"))
    
    # 直接在RGB数组上操作，避免额外的颜色空间转换
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    mask = np.zeros(bgr.shape[:2], np.uint8)
    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)

    try:
        # 减少迭代次数以提高性能
        cv2.grabCut(bgr, mask, rect, bgd_model, fgd_model, 3, cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        return _replace_background_simple(image, background_color, feather)

    # 直接在mask上操作，避免创建新的keep数组
    keep = np.zeros(mask.shape, dtype=np.float32)
    keep[(mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD)] = 1.0

    # 使用in-place操作减少内存复制
    kernel = np.ones((3, 3), np.uint8)
    keep = cv2.morphologyEx(keep, cv2.MORPH_CLOSE, kernel, iterations=1)

    if feather > 0:
        ksize = max(3, feather * 2 + 1)
        keep = cv2.GaussianBlur(keep, (ksize, ksize), 0)
        np.clip(keep, 0.0, 1.0, out=keep)  # in-place操作

    # 准备背景
    if background_image is not None:
        # 调整背景图像大小以匹配原始图像
        background = background_image.resize((width, height), Image.Resampling.LANCZOS)
        bg_rgb = np.array(background.convert("RGB"), dtype=np.float32)
    else:
        # 使用背景颜色
        bg_rgb = np.array(_hex_to_rgba(background_color)[:3], dtype=np.float32)

    # 直接在rgb数组上进行计算，减少内存分配
    rgb_float = rgb.astype(np.float32)
    comp = rgb_float * keep[..., None] + bg_rgb * (1.0 - keep[..., None])
    np.clip(comp, 0, 255, out=comp)
    comp = comp.astype(np.uint8)
    
    return Image.fromarray(comp).convert("RGBA")


def _process_large_image_in_chunks(
    image: Image.Image,
    background_color: str,
    feather: int,
    background_image: Image.Image | None,
    rect: tuple[int, int, int, int],
) -> Image.Image:
    """分块处理大图像，减少内存使用"""
    width, height = image.size
    chunk_size = 2048  # 每个块的大小
    
    # 准备背景
    if background_image is not None:
        background = background_image.resize((width, height), Image.Resampling.LANCZOS)
    else:
        background = Image.new("RGB", (width, height), _hex_to_rgba(background_color)[:3])
    
    # 创建结果图像
    result = Image.new("RGBA", (width, height))
    
    # 分块处理
    for y in range(0, height, chunk_size):
        for x in range(0, width, chunk_size):
            # 计算块的边界
            chunk_width = min(chunk_size, width - x)
            chunk_height = min(chunk_size, height - y)
            
            # 提取块
            chunk = image.crop((x, y, x + chunk_width, y + chunk_height))
            
            # 处理块
            processed_chunk = _replace_background_simple(
                chunk, background_color, feather
            )
            
            # 将处理后的块粘贴到结果图像
            result.paste(processed_chunk, (x, y))
    
    return result


@dataclass
class ProcessedArtifact:
    task_id: str
    output_path: Path
    result_url: str
    download_url: str
    meta: ResultMeta
    created_at: str

    def to_task_response(self) -> TaskDetailResponse:
        return TaskDetailResponse(
            task_id=self.task_id,
            result_url=self.result_url,
            download_url=self.download_url,
            meta=self.meta,
            created_at=self.created_at,
        )


def _save_output_artifact(
    image: Image.Image,
    *,
    output: OutputOptions | BasicOutputOptions,
    output_dir: Path,
    preset_name: str | None,
    fallback_prefix: str,
    task_id: str | None = None,
) -> ProcessedArtifact:
    task_id = task_id or uuid4().hex
    filename = _sanitize_filename(
        output.filename,
        fallback=f"{fallback_prefix}-{task_id[:8]}",
        output_format=output.format,
    )
    extension = ".jpg" if output.format == "jpg" else ".png"
    output_path = output_dir / f"{task_id}{extension}"
    tmp_path = output_dir / f"{task_id}{extension}.tmp"

    if output.format == "jpg":
        rgba = image.convert("RGBA")
        rgb = Image.new("RGB", rgba.size, _hex_to_rgba(output.background_color)[:3])
        rgb.paste(rgba, mask=rgba.getchannel("A"))

        if isinstance(output, OutputOptions):
            encoded = _compress_jpeg_to_target(rgb, output)
        else:
            encoded = _encode_rgb_jpeg(rgb, output.dpi, output.quality)
    else:
        buffer = io.BytesIO()
        image.convert("RGBA").save(
            buffer,
            format="PNG",
            optimize=True,
            compress_level=9,
            dpi=(output.dpi, output.dpi),
        )
        encoded = buffer.getvalue()

    tmp_path.write_bytes(encoded)
    tmp_path.replace(output_path)

    meta = ResultMeta(
        width_px=image.width,
        height_px=image.height,
        format=output.format,
        dpi=output.dpi,
        size_kb=round(len(encoded) / 1024, 2),
        filename=filename,
        background_color=output.background_color,
        preset_name=preset_name,
    )
    created_at = datetime.now(timezone.utc).isoformat()

    result_url = f"/api/v1/files/result/{task_id}"
    download_url = f"/api/v1/files/download/{task_id}"

    return ProcessedArtifact(
        task_id=task_id,
        output_path=output_path,
        result_url=result_url,
        download_url=download_url,
        meta=meta,
        created_at=created_at,
    )


def _load_supported_source(
    source_path: Path,
    *,
    convert_mode: str | None,
    too_large_message: str,
    invalid_image_message: str,
) -> tuple[Image.Image, str]:
    try:
        with Image.open(source_path) as raw_image:
            if raw_image.width * raw_image.height > MAX_IMAGE_PIXELS:
                raise ValueError(too_large_message)

            fmt = (raw_image.format or source_path.suffix.lstrip(".")).upper()
            if fmt not in {"JPEG", "JPG", "PNG"}:
                raise ValueError("仅支持 JPG、JPEG、PNG 格式。")

            prepared = ImageOps.exif_transpose(raw_image)
            prepared.load()
            if convert_mode:
                prepared = prepared.convert(convert_mode)
            return prepared, fmt.lower()
    except Image.DecompressionBombError as exc:
        raise ValueError(too_large_message) from exc
    except OSError as exc:
        raise ValueError(invalid_image_message) from exc


class ImageService:
    def inspect_image(self, source_path: Path) -> ImageInfo:
        prepared, fmt = _load_supported_source(
            source_path,
            convert_mode=None,
            too_large_message="图片像素过大，请压缩后再上传（建议小于 25MP）。",
            invalid_image_message="上传文件不是有效图片。",
        )
        return ImageInfo(
            width_px=prepared.width,
            height_px=prepared.height,
            format=fmt,
        )

    def process_image(
        self,
        source_path: Path,
        request: ProcessRequest,
        output_dir: Path,
        preset_name: str | None = None,
        task_id: str | None = None,
    ) -> ProcessedArtifact:
        # 生成缓存键
        params = {
            "custom_size": request.custom_size.model_dump(),
            "render": request.render.model_dump(),
            "adjustments": request.adjustments.model_dump(),
            "output": request.output.model_dump(),
            "preset_name": preset_name,
        }
        cache_key = _generate_cache_key(source_path, params)
        extension = "jpg" if request.output.format == "jpg" else "png"
        cache_path = _get_cache_path(cache_key, extension)
        
        # 检查缓存是否有效
        if _is_cache_valid(cache_path):
            # 从缓存中读取结果
            response_task_id = task_id or uuid4().hex
            output_path = output_dir / f"{response_task_id}.{extension}"
            
            # 如果缓存文件不存在于输出目录，复制过去
            if not output_path.exists():
                import shutil
                shutil.copy2(cache_path, output_path)
            
            # 计算文件大小
            size_kb = round(output_path.stat().st_size / 1024, 2)
            
            # 构建返回结果
            filename = _sanitize_filename(
                request.output.filename,
                fallback=f"result-{response_task_id[:8]}",
                output_format=request.output.format,
            )
            
            meta = ResultMeta(
                width_px=0,  # 这里需要从图像中读取实际尺寸
                height_px=0,  # 这里需要从图像中读取实际尺寸
                format=request.output.format,
                dpi=request.output.dpi,
                size_kb=size_kb,
                filename=filename,
                background_color=request.output.background_color,
                preset_name=preset_name,
            )
            
            # 读取图像尺寸
            try:
                with Image.open(output_path) as img:
                    meta.width_px = img.width
                    meta.height_px = img.height
            except Exception:
                pass
            
            created_at = datetime.now(timezone.utc).isoformat()
            result_url = f"/api/v1/files/result/{response_task_id}"
            download_url = f"/api/v1/files/download/{response_task_id}"
            
            return ProcessedArtifact(
                task_id=response_task_id,
                output_path=output_path,
                result_url=result_url,
                download_url=download_url,
                meta=meta,
                created_at=created_at,
            )
        
        # 缓存无效，执行正常处理流程
        target_width, target_height = resolve_output_size(request.custom_size)
        if target_width * target_height > MAX_IMAGE_PIXELS:
            raise ValueError("输出尺寸过大，建议降低尺寸或 DPI（建议小于 25MP）。")

        prepared, _ = _load_supported_source(
            source_path,
            convert_mode="RGBA",
            too_large_message="图片像素过大，无法处理（建议小于 25MP）。",
            invalid_image_message="原始图片文件损坏，请重新上传。",
        )

        composed = _render_viewport(
            source=prepared,
            render=request.render,
            target_width=target_width,
            target_height=target_height,
            background_color=request.output.background_color,
        )
        adjusted = _apply_adjustments(composed, request.adjustments)
        if request.output.replace_background:
            # 处理背景图像
            background_image = None
            if request.output.background_image_id:
                from app.services.storage_service import storage_service
                background_path = storage_service.get_upload_path(request.output.background_image_id)
                if background_path:
                    try:
                        background_image = Image.open(background_path)
                        background_image.load()
                    except Exception:
                        # 背景图像加载失败，使用背景颜色
                        background_image = None
            
            adjusted = _replace_background_grabcut(
                adjusted,
                background_color=request.output.background_color,
                feather=request.output.replace_feather,
                background_image=background_image,
            )
        
        # 保存结果
        artifact = _save_output_artifact(
            adjusted,
            output=request.output,
            output_dir=output_dir,
            preset_name=preset_name,
            fallback_prefix="result",
            task_id=task_id,
        )
        
        # 将结果写入缓存
        try:
            import shutil
            shutil.copy2(artifact.output_path, cache_path)
        except Exception:
            pass
        
        # 清理过期缓存
        _cleanup_expired_cache()
        
        return artifact

    def suggest_render(self, source_path: Path, request: SuggestRenderRequest) -> tuple[RenderState, FaceBox | None]:
        prepared, _ = _load_supported_source(
            source_path,
            convert_mode="RGB",
            too_large_message="图片像素过大，无法分析（建议小于 25MP）。",
            invalid_image_message="原始图片文件损坏，请重新上传。",
        )

        width, height = prepared.size
        rgb = np.array(prepared)
        face = face_service.detect_largest_face(rgb)

        width_scale = request.viewport_width / width
        height_scale = request.viewport_height / height
        base_scale = max(width_scale, height_scale) if request.fit_mode == FitMode.FILL else min(width_scale, height_scale)

        if face:
            desired = request.viewport_height * request.face_height_ratio / max(1, face.height)
            scale = max(base_scale, desired)
        else:
            scale = base_scale

        scale = _clamp(scale, base_scale * 0.9, base_scale * 3.5)

        if face:
            face_cx = face.center_x
            face_cy = face.center_y
        else:
            face_cx = width / 2
            face_cy = height * 0.42

        anchor_y_px = request.viewport_height * request.anchor_y
        offset_x = (width / 2 - face_cx) * scale
        offset_y = anchor_y_px - request.viewport_height / 2 + (height / 2 - face_cy) * scale

        display_w = width * scale
        display_h = height * scale
        max_off_x = max(0.0, (display_w - request.viewport_width) / 2)
        max_off_y = max(0.0, (display_h - request.viewport_height) / 2)

        offset_x = _clamp(offset_x, -max_off_x, max_off_x)
        offset_y = _clamp(offset_y, -max_off_y, max_off_y)

        return (
            RenderState(
                viewport_width=request.viewport_width,
                viewport_height=request.viewport_height,
                scale=scale,
                offset_x=offset_x,
                offset_y=offset_y,
                fit_mode=request.fit_mode,
            ),
            face,
        )

    def compose_sheet(
        self,
        source_path: Path,
        page_size,
        *,
        margin_mm: float,
        gap_mm: float,
        cols: int | None,
        rows: int | None,
        copies: int | None,
        show_cut_lines: bool,
        cut_line_color: str,
        cut_line_width: int,
        output,
        output_dir: Path,
        preset_name: str | None = None,
        task_id: str | None = None,
    ) -> ProcessedArtifact:
        page_width, page_height = resolve_output_size(page_size)
        if page_width * page_height > MAX_IMAGE_PIXELS:
            raise ValueError("排版画布过大，建议降低纸张 DPI（建议小于 25MP）。")

        dpi = page_size.dpi
        margin_px = _mm_to_px(margin_mm, dpi)
        gap_px = _mm_to_px(gap_mm, dpi)

        photo_rgba, _ = _load_supported_source(
            source_path,
            convert_mode="RGBA",
            too_large_message="排版原图过大，无法处理（建议小于 25MP）。",
            invalid_image_message="原始图片文件损坏，请重新上传。",
        )

        photo_w, photo_h = photo_rgba.size
        available_w = max(1, page_width - margin_px * 2)
        available_h = max(1, page_height - margin_px * 2)

        max_cols = max(1, int((available_w + gap_px) // (photo_w + gap_px)))
        max_rows = max(1, int((available_h + gap_px) // (photo_h + gap_px)))

        grid_cols = cols or max_cols
        grid_rows = rows or max_rows

        if grid_cols > max_cols or grid_rows > max_rows:
            raise ValueError("排版行列超出纸张可容纳范围，请减小行列数或降低边距/间距。")

        max_slots = grid_cols * grid_rows
        target_copies = min(copies or max_slots, max_slots)

        canvas = Image.new("RGBA", (page_width, page_height), _hex_to_rgba(output.background_color))

        grid_w = grid_cols * photo_w + (grid_cols - 1) * gap_px
        grid_h = grid_rows * photo_h + (grid_rows - 1) * gap_px
        start_x = margin_px + max(0, int(round((available_w - grid_w) / 2)))
        start_y = margin_px + max(0, int(round((available_h - grid_h) / 2)))

        for index in range(target_copies):
            row = index // grid_cols
            col = index % grid_cols
            x = start_x + col * (photo_w + gap_px)
            y = start_y + row * (photo_h + gap_px)
            canvas.paste(photo_rgba, (x, y), photo_rgba)
            if show_cut_lines:
                _draw_cut_marks(canvas, x, y, photo_w, photo_h, cut_line_color, cut_line_width)
        return _save_output_artifact(
            canvas,
            output=output,
            output_dir=output_dir,
            preset_name=preset_name,
            fallback_prefix="sheet",
            task_id=task_id,
        )

    def resize_image(
        self,
        source_path: Path,
        request: ResizeRequest,
        output_dir: Path,
        preset_name: str | None = None,
        task_id: str | None = None,
    ) -> ProcessedArtifact:
        if request.width_px * request.height_px > MAX_IMAGE_PIXELS:
            raise ValueError("输出尺寸过大，建议降低宽高（建议小于 25MP）。")

        prepared, _ = _load_supported_source(
            source_path,
            convert_mode="RGBA",
            too_large_message="图片像素过大，无法处理（建议小于 25MP）。",
            invalid_image_message="原始图片文件损坏，请重新上传。",
        )

        resized = prepared.resize((request.width_px, request.height_px), Image.Resampling.LANCZOS)
        return _save_output_artifact(
            resized,
            output=request.output,
            output_dir=output_dir,
            preset_name=preset_name,
            fallback_prefix="resized",
            task_id=task_id,
        )

    def enhance_image(
        self,
        source_path: Path,
        request: EnhanceRequest,
        output_dir: Path,
        preset_name: str | None = None,
        task_id: str | None = None,
    ) -> ProcessedArtifact:
        prepared, _ = _load_supported_source(
            source_path,
            convert_mode=None,
            too_large_message="图片像素过大，无法处理（建议小于 25MP）。",
            invalid_image_message="原始图片文件损坏，请重新上传。",
        )

        alpha = prepared.getchannel("A") if "A" in prepared.getbands() else None
        working = prepared.convert("RGB")

        if request.scale_factor != 1:
            target_width = max(1, round(working.width * request.scale_factor))
            target_height = max(1, round(working.height * request.scale_factor))
            if target_width * target_height > MAX_IMAGE_PIXELS:
                raise ValueError("增强后的输出尺寸过大，建议降低放大倍率（建议小于 25MP）。")

            if cv2 is not None:
                interpolation = cv2.INTER_CUBIC if request.scale_factor > 1 else cv2.INTER_AREA
                array = cv2.resize(
                    np.array(working),
                    (target_width, target_height),
                    interpolation=interpolation,
                )
                working = Image.fromarray(array)
            else:
                working = working.resize((target_width, target_height), Image.Resampling.LANCZOS)

            if alpha is not None:
                alpha = alpha.resize((target_width, target_height), Image.Resampling.LANCZOS)

        if request.denoise:
            if cv2 is not None:
                strength = max(3, int(round(request.denoise * 0.9)))
                array = cv2.fastNlMeansDenoisingColored(
                    np.array(working),
                    None,
                    strength,
                    strength,
                    7,
                    21,
                )
                working = Image.fromarray(array)
            else:
                blur_radius = max(0.5, request.denoise / 18)
                working = working.filter(ImageFilter.MedianFilter(size=3))
                working = working.filter(ImageFilter.GaussianBlur(radius=blur_radius))

        if request.auto_contrast:
            working = ImageOps.autocontrast(working, cutoff=1)

        if request.contrast:
            factor = max(0.2, 1 + request.contrast / 100)
            working = ImageEnhance.Contrast(working).enhance(factor)

        if request.sharpness:
            radius = 1.4 if request.scale_factor <= 1.5 else 1.8
            percent = 100 + request.sharpness * 5
            threshold = 2 if request.denoise else 3
            working = working.filter(
                ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold)
            )

        enhanced = working.convert("RGBA")
        if alpha is not None:
            enhanced.putalpha(alpha)

        return _save_output_artifact(
            enhanced,
            output=request.output,
            output_dir=output_dir,
            preset_name=preset_name,
            fallback_prefix="enhanced",
            task_id=task_id,
        )


image_service = ImageService()

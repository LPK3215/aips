from pathlib import Path

from PIL import Image

from app.schemas.images import (
    Adjustments,
    CustomSize,
    EnhanceRequest,
    OutputOptions,
    ProcessRequest,
    RenderState,
    ResizeRequest,
)
from app.services import image_service as image_service_module
from app.services.face_service import face_service
from app.services.image_service import image_service


def test_process_image_generates_real_output(tmp_path: Path) -> None:
    source_path = tmp_path / "source.png"
    source = Image.new("RGB", (1200, 1600), "#d4c8b8")
    source.save(source_path, format="PNG")

    request = ProcessRequest(
        file_id="demo",
        custom_size=CustomSize(width=413, height=626, unit="px", dpi=300),
        render=RenderState(
            viewport_width=320,
            viewport_height=486,
            scale=0.32,
            offset_x=0,
            offset_y=0,
            fit_mode="fill",
        ),
        adjustments=Adjustments(sharpness=20),
        output=OutputOptions(
            format="jpg",
            dpi=300,
            quality=90,
            target_size_kb_min=20,
            target_size_kb_max=250,
            filename="kaoyan-output.jpg",
            background_color="#f5f1e8",
        ),
    )

    artifact = image_service.process_image(source_path, request, tmp_path, preset_name="考研报名")

    assert artifact.output_path.exists()
    assert artifact.meta.width_px == 413
    assert artifact.meta.height_px == 626
    assert artifact.meta.format == "jpg"
    assert artifact.meta.filename == "kaoyan-output.jpg"
    assert artifact.result_url.endswith(artifact.task_id)
    assert artifact.download_url.endswith(artifact.task_id)

    with Image.open(artifact.output_path) as result:
        assert result.size == (413, 626)
        assert result.format == "JPEG"


def test_inspect_image_respects_exif_orientation(tmp_path: Path) -> None:
    source_path = tmp_path / "rotated.jpg"
    source = Image.new("RGB", (300, 500), "#d4c8b8")
    exif = Image.Exif()
    exif[274] = 6
    source.save(source_path, format="JPEG", exif=exif)

    info = image_service.inspect_image(source_path)

    assert info.width_px == 500
    assert info.height_px == 300
    assert info.format == "jpeg"


def test_process_image_falls_back_without_opencv(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(image_service_module, "cv2", None)
    monkeypatch.setattr(face_service, "_available", False)
    monkeypatch.setattr(face_service, "_cascade", None)

    source_path = tmp_path / "source.png"
    source = Image.new("RGB", (900, 1200), "#d7d7d7")
    source.paste(Image.new("RGB", (380, 620), "#4d3b30"), (260, 180))
    source.save(source_path, format="PNG")

    request = ProcessRequest(
        file_id="demo",
        custom_size=CustomSize(width=295, height=413, unit="px", dpi=300),
        render=RenderState(
            viewport_width=295,
            viewport_height=413,
            scale=1,
            offset_x=0,
            offset_y=0,
            fit_mode="fill",
        ),
        adjustments=Adjustments(blur=4),
        output=OutputOptions(
            format="jpg",
            dpi=300,
            quality=90,
            filename="fallback-output.jpg",
            background_color="#ffffff",
            replace_background=True,
            replace_feather=8,
        ),
    )

    artifact = image_service.process_image(source_path, request, tmp_path, preset_name="自定义")

    assert artifact.output_path.exists()
    with Image.open(artifact.output_path) as result:
        assert result.size == (295, 413)
        assert result.format == "JPEG"


def test_compress_jpeg_to_target_respects_quality_cap(monkeypatch) -> None:
    attempted_qualities: list[int] = []

    def fake_encode_rgb_jpeg(_image: Image.Image, _dpi: int, quality: int) -> bytes:
        attempted_qualities.append(quality)
        return b"x" * (quality * 1024)

    monkeypatch.setattr(image_service_module, "_encode_rgb_jpeg", fake_encode_rgb_jpeg)

    image = Image.new("RGB", (64, 64), "#ffffff")
    output = OutputOptions(
        format="jpg",
        dpi=300,
        quality=60,
        target_size_kb_min=90,
        target_size_kb_max=120,
        filename="quality-cap.jpg",
        background_color="#ffffff",
    )

    data = image_service_module._compress_jpeg_to_target(image, output)

    assert attempted_qualities
    assert max(attempted_qualities) <= output.quality
    assert len(data) == output.quality * 1024


def test_resize_image_generates_exact_dimensions(tmp_path: Path) -> None:
    source_path = tmp_path / "source.png"
    source = Image.new("RGBA", (1200, 800), "#d4c8b8")
    source.save(source_path, format="PNG")

    artifact = image_service.resize_image(
        source_path,
        ResizeRequest(
            file_id="resize-demo",
            width_px=600,
            height_px=400,
            output={
                "format": "png",
                "dpi": 300,
                "quality": 90,
                "filename": "resized-output",
                "background_color": "#ffffff",
            },
        ),
        tmp_path,
        preset_name="图片缩放",
    )

    assert artifact.output_path.exists()
    assert artifact.meta.width_px == 600
    assert artifact.meta.height_px == 400
    assert artifact.meta.preset_name == "图片缩放"

    with Image.open(artifact.output_path) as result:
        assert result.size == (600, 400)
        assert result.format == "PNG"


def test_enhance_image_can_upscale_and_sharpen(tmp_path: Path) -> None:
    source_path = tmp_path / "source.png"
    source = Image.new("RGB", (320, 240), "#b9c6cf")
    source.paste(Image.new("RGB", (120, 120), "#4f3f35"), (100, 60))
    source.save(source_path, format="PNG")

    artifact = image_service.enhance_image(
        source_path,
        EnhanceRequest(
            file_id="enhance-demo",
            scale_factor=2.0,
            denoise=8,
            sharpness=36,
            contrast=10,
            auto_contrast=True,
            output={
                "format": "jpg",
                "dpi": 300,
                "quality": 88,
                "filename": "enhanced-output",
                "background_color": "#ffffff",
            },
        ),
        tmp_path,
        preset_name="清晰增强",
    )

    assert artifact.output_path.exists()
    assert artifact.meta.width_px == 640
    assert artifact.meta.height_px == 480
    assert artifact.meta.preset_name == "清晰增强"

    with Image.open(artifact.output_path) as result:
        assert result.size == (640, 480)
        assert result.format == "JPEG"

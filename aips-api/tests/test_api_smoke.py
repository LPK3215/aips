import io
import time
import zipfile

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.services.rate_limit_service import RateLimitBucket, rate_limit_service
from app.services.storage_service import storage_service
from app.services.task_service import task_service


def wait_for_task_completion(client: TestClient, task_id: str, *, timeout_seconds: float = 30.0) -> dict:
    deadline = time.time() + timeout_seconds
    last_status: dict | None = None

    while time.time() < deadline:
        status_response = client.get(f"/api/v1/tasks/{task_id}/status")
        assert status_response.status_code == 200
        last_status = status_response.json()

        if last_status["status"] == "completed":
            task_response = client.get(f"/api/v1/tasks/{task_id}")
            assert task_response.status_code == 200
            return task_response.json()

        if last_status["status"] == "failed":
            raise AssertionError(f"task {task_id} failed: {last_status['message']}")

        time.sleep(0.05)

    raise AssertionError(f"task {task_id} did not complete in time: {last_status}")


def test_api_upload_process_download_flow() -> None:
    client = TestClient(app)
    client.__enter__()

    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    presets = client.get("/api/v1/presets")
    assert presets.status_code == 200
    payload = presets.json()
    assert payload["items"]

    buffer = io.BytesIO()
    source = Image.new("RGB", (600, 900), "#d4c8b8")
    source.save(buffer, format="PNG")
    buffer.seek(0)

    upload = client.post(
        "/api/v1/files/upload",
        files={"file": ("sample.png", buffer.getvalue(), "image/png")},
    )
    assert upload.status_code == 201
    upload_json = upload.json()
    file_id = upload_json["file_id"]

    suggest = client.post(
        "/api/v1/images/suggest-render",
        json={
            "file_id": file_id,
            "custom_size": {"width": 413, "height": 626, "unit": "px", "dpi": 300},
            "viewport_width": 320,
            "viewport_height": 486,
            "fit_mode": "fill",
            "anchor_y": 0.42,
            "face_height_ratio": 0.55,
        },
    )
    assert suggest.status_code == 200
    suggest_json = suggest.json()
    assert suggest_json["render"]["scale"] > 0

    process = client.post(
        "/api/v1/images/process",
        json={
            "file_id": file_id,
            "preset_id": None,
            "custom_size": {"width": 413, "height": 626, "unit": "px", "dpi": 300},
            "render": suggest_json["render"],
            "adjustments": {
                "brightness": 0,
                "contrast": 0,
                "saturation": 0,
                "sharpness": 20,
                "blur": 0,
            },
            "output": {
                "format": "jpg",
                "dpi": 300,
                "quality": 90,
                "target_size_kb_min": None,
                "target_size_kb_max": 250,
                "filename": "e2e-smoke",
                "background_color": "#f5f1e8",
                "replace_background": False,
                "replace_feather": 6,
            },
        },
    )
    assert process.status_code == 201
    process_json = process.json()
    task_id = process_json["task_id"]
    result_url = process_json["result_url"]
    assert process_json["download_url"].endswith(task_id)
    assert process_json["meta"] is None

    task_json = wait_for_task_completion(client, task_id)
    assert task_json["file_available"] is True
    assert task_json["meta"]["width_px"] == 413
    assert task_json["meta"]["height_px"] == 626
    assert task_json["download_url"].endswith(task_id)

    preview = client.get(result_url)
    assert preview.status_code == 200
    assert preview.headers["content-type"].startswith("image/")

    with Image.open(io.BytesIO(preview.content)) as result_image:
        assert result_image.size == (413, 626)

    download = client.get(task_json["download_url"])
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("image/")

    sheet = client.post(
        "/api/v1/images/compose-sheet",
        json={
            "task_id": task_id,
            "page_size": {"width": 4, "height": 6, "unit": "inch", "dpi": 150},
            "margin_mm": 6,
            "gap_mm": 4,
            "cols": 1,
            "rows": 1,
            "copies": 1,
            "show_cut_lines": True,
            "cut_line_color": "#1b1b1b",
            "cut_line_width": 2,
            "output": {
                "format": "jpg",
                "dpi": 300,
                "quality": 92,
                "filename": "print-sheet-a4",
                "background_color": "#ffffff",
            },
        },
    )
    assert sheet.status_code == 201
    sheet_json = sheet.json()
    sheet_task_id = sheet_json["task_id"]
    assert sheet_json["download_url"].endswith(sheet_task_id)
    assert sheet_json["meta"] is None

    wait_for_task_completion(client, sheet_task_id)
    sheet_preview = client.get(sheet_json["result_url"])
    assert sheet_preview.status_code == 200
    with Image.open(io.BytesIO(sheet_preview.content)) as sheet_image:
        assert sheet_image.size == (600, 900)

    # Cleanup files created during the test.
    upload_path = storage_service.get_upload_path(file_id)
    if upload_path:
        storage_service.delete_path(upload_path)

    task_detail = task_service.get_task(task_id)
    if task_detail:
        storage_service.delete_path(storage_service.get_result_path(task_id, task_detail.meta.format))
        storage_service.delete_path(task_service._task_path(task_id))

    sheet_detail = task_service.get_task(sheet_task_id)
    if sheet_detail:
        storage_service.delete_path(
            storage_service.get_result_path(sheet_task_id, sheet_detail.meta.format)
        )
        storage_service.delete_path(task_service._task_path(sheet_task_id))


def test_api_batch_auto_process_flow() -> None:
    client = TestClient(app)
    client.__enter__()
    existing_temp_archives = {path.name for path in storage_service.temp_dir.glob("*.zip.tmp")}

    def upload_png() -> str:
        buffer = io.BytesIO()
        source = Image.new("RGB", (520, 760), "#d4c8b8")
        source.save(buffer, format="PNG")
        buffer.seek(0)
        response = client.post(
            "/api/v1/files/upload",
            files={"file": ("batch.png", buffer.getvalue(), "image/png")},
        )
        assert response.status_code == 201
        return response.json()["file_id"]

    file_ids = [upload_png(), upload_png()]

    batch = client.post(
        "/api/v1/images/process-batch-auto",
        json={
            "file_ids": file_ids,
            "preset_id": None,
            "custom_size": {"width": 413, "height": 626, "unit": "px", "dpi": 300},
            "viewport_width": 320,
            "viewport_height": 486,
            "fit_mode": "fill",
            "anchor_y": 0.42,
            "face_height_ratio": 0.55,
            "adjustments": {
                "brightness": 0,
                "contrast": 0,
                "saturation": 0,
                "sharpness": 18,
                "blur": 0,
            },
            "output": {
                "format": "jpg",
                "dpi": 300,
                "quality": 88,
                "target_size_kb_min": None,
                "target_size_kb_max": 250,
                "filename": "batch-export",
                "background_color": "#f5f1e8",
                "replace_background": False,
                "replace_feather": 6,
            },
        },
    )
    assert batch.status_code == 200
    payload = batch.json()
    assert len(payload["items"]) == 2
    assert all(item["ok"] for item in payload["items"])

    task_ids = [item["task_id"] for item in payload["items"]]
    for task_id in task_ids:
        task = client.get(f"/api/v1/tasks/{task_id}")
        assert task.status_code == 200

    recent = client.get("/api/v1/tasks?limit=10")
    assert recent.status_code == 200
    recent_payload = recent.json()
    assert "missing_count" in recent_payload

    zip_response = client.post(
        "/api/v1/files/download-zip",
        json={"task_ids": task_ids, "filename": "batch-test", "include_manifest": True},
    )
    assert zip_response.status_code == 200
    assert zip_response.headers["content-type"].startswith("application/zip")
    assert 'filename="batch-test.zip"' in zip_response.headers["content-disposition"]

    with zipfile.ZipFile(io.BytesIO(zip_response.content)) as archive:
        names = archive.namelist()
        assert "manifest.json" in names
        exported = [name for name in names if name.lower().endswith((".jpg", ".png"))]
        assert len(exported) == 2

    current_temp_archives = {path.name for path in storage_service.temp_dir.glob("*.zip.tmp")}
    assert current_temp_archives == existing_temp_archives

    # Cleanup
    for file_id in file_ids:
        upload_path = storage_service.get_upload_path(file_id)
        if upload_path:
            storage_service.delete_path(upload_path)

    for task_id in task_ids:
        task_detail = task_service.get_task(task_id)
        if task_detail:
            storage_service.delete_path(storage_service.get_result_path(task_id, task_detail.meta.format))
            storage_service.delete_path(task_service._task_path(task_id))


def test_api_upload_returns_specific_validation_error() -> None:
    client = TestClient(app)
    client.__enter__()

    response = client.post(
        "/api/v1/files/upload",
        files={"file": ("sample.gif", b"GIF89a", "image/gif")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "仅支持 JPG、JPEG、PNG 格式。"


def test_api_task_detail_marks_missing_result_and_hides_from_recent_list() -> None:
    client = TestClient(app)
    client.__enter__()

    buffer = io.BytesIO()
    source = Image.new("RGB", (600, 900), "#d4c8b8")
    source.save(buffer, format="PNG")
    buffer.seek(0)

    upload = client.post(
        "/api/v1/files/upload",
        files={"file": ("sample.png", buffer.getvalue(), "image/png")},
    )
    assert upload.status_code == 201
    file_id = upload.json()["file_id"]

    process = client.post(
        "/api/v1/images/process",
        json={
            "file_id": file_id,
            "preset_id": None,
            "custom_size": {"width": 413, "height": 626, "unit": "px", "dpi": 300},
            "render": {
                "viewport_width": 320,
                "viewport_height": 486,
                "scale": 0.32,
                "offset_x": 0,
                "offset_y": 0,
                "fit_mode": "fill",
            },
            "adjustments": {
                "brightness": 0,
                "contrast": 0,
                "saturation": 0,
                "sharpness": 18,
                "blur": 0,
            },
            "output": {
                "format": "jpg",
                "dpi": 300,
                "quality": 90,
                "target_size_kb_min": None,
                "target_size_kb_max": 250,
                "filename": "missing-check",
                "background_color": "#ffffff",
                "replace_background": False,
                "replace_feather": 6,
            },
        },
    )
    assert process.status_code == 201
    task_id = process.json()["task_id"]

    task_json = wait_for_task_completion(client, task_id)
    task_detail = task_service.get_task(task_json["task_id"])
    assert task_detail is not None
    result_path = storage_service.get_result_path(task_id, task_detail.meta.format)
    storage_service.delete_path(result_path)

    detail = client.get(f"/api/v1/tasks/{task_id}")
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["file_available"] is False

    recent = client.get("/api/v1/tasks?limit=10")
    assert recent.status_code == 200
    recent_payload = recent.json()
    assert recent_payload["missing_count"] >= 1
    assert all(item["task_id"] != task_id for item in recent_payload["items"])

    recent_with_missing = client.get("/api/v1/tasks?limit=10&include_missing=true")
    assert recent_with_missing.status_code == 200
    recent_with_missing_payload = recent_with_missing.json()
    target = next(item for item in recent_with_missing_payload["items"] if item["task_id"] == task_id)
    assert target["file_available"] is False

    download = client.get(f"/api/v1/files/download/{task_id}")
    assert download.status_code == 410
    assert download.json()["detail"] == "处理结果文件已过期被清理。"

    upload_path = storage_service.get_upload_path(file_id)
    if upload_path:
        storage_service.delete_path(upload_path)
    storage_service.delete_path(task_service._task_path(task_id))


def test_api_upload_rate_limit_and_cache_headers() -> None:
    client = TestClient(app)
    client.__enter__()
    original_bucket = rate_limit_service.buckets["upload"]
    rate_limit_service.buckets["upload"] = RateLimitBucket(limit=1, window_seconds=60)
    request_id = "req-upload-test-01"

    try:
        presets = client.get("/api/v1/presets")
        assert presets.status_code == 200
        assert presets.headers["cache-control"] == "public, max-age=300"
        assert "x-request-id" in presets.headers

        tasks = client.get("/api/v1/tasks?limit=5")
        assert tasks.status_code == 200
        assert tasks.headers["cache-control"] == "no-store"
        assert "x-request-id" in tasks.headers

        buffer = io.BytesIO()
        source = Image.new("RGB", (600, 800), "#d4c8b8")
        source.save(buffer, format="PNG")
        payload = buffer.getvalue()

        first = client.post(
            "/api/v1/files/upload",
            files={"file": ("rate-limit.png", payload, "image/png")},
            headers={"X-Request-ID": request_id},
        )
        assert first.status_code == 201
        assert first.headers["x-ratelimit-limit"] == "1"
        assert first.headers["x-ratelimit-remaining"] == "0"
        assert first.headers["cache-control"] == "no-store"
        assert first.headers["x-request-id"] == request_id
        file_id = first.json()["file_id"]

        second = client.post(
            "/api/v1/files/upload",
            files={"file": ("rate-limit.png", payload, "image/png")},
            headers={"X-Request-ID": request_id},
        )
        assert second.status_code == 429
        assert second.headers["retry-after"] == "60"
        assert second.headers["cache-control"] == "no-store"
        assert second.headers["x-request-id"] == request_id

        upload_path = storage_service.get_upload_path(file_id)
        if upload_path:
            storage_service.delete_path(upload_path)
    finally:
        rate_limit_service.buckets["upload"] = original_bucket


def test_api_resize_and_enhance_flow() -> None:
    client = TestClient(app)
    client.__enter__()

    buffer = io.BytesIO()
    source = Image.new("RGB", (640, 480), "#d4c8b8")
    source.paste(Image.new("RGB", (200, 220), "#4f3f35"), (220, 100))
    source.save(buffer, format="PNG")
    payload = buffer.getvalue()

    upload = client.post(
        "/api/v1/files/upload",
        files={"file": ("tool-sample.png", payload, "image/png")},
    )
    assert upload.status_code == 201
    file_id = upload.json()["file_id"]

    resize = client.post(
        "/api/v1/images/resize",
        json={
            "file_id": file_id,
            "width_px": 320,
            "height_px": 240,
            "output": {
                "format": "png",
                "dpi": 300,
                "quality": 90,
                "filename": "tool-resized",
                "background_color": "#ffffff",
            },
        },
    )
    assert resize.status_code == 201
    resize_json = resize.json()
    resize_task_id = resize_json["task_id"]
    assert resize_json["meta"] is None
    resize_task = wait_for_task_completion(client, resize_task_id)
    assert resize_task["meta"]["preset_name"] == "图片缩放"

    resize_preview = client.get(resize_json["result_url"])
    assert resize_preview.status_code == 200
    with Image.open(io.BytesIO(resize_preview.content)) as resized_image:
        assert resized_image.size == (320, 240)

    enhance = client.post(
        "/api/v1/images/enhance",
        json={
            "file_id": file_id,
            "scale_factor": 1.5,
            "denoise": 8,
            "sharpness": 32,
            "contrast": 10,
            "auto_contrast": True,
            "output": {
                "format": "jpg",
                "dpi": 300,
                "quality": 88,
                "filename": "tool-enhanced",
                "background_color": "#ffffff",
            },
        },
    )
    assert enhance.status_code == 201
    enhance_json = enhance.json()
    enhance_task_id = enhance_json["task_id"]
    assert enhance_json["meta"] is None
    enhance_task = wait_for_task_completion(client, enhance_task_id)
    assert enhance_task["meta"]["preset_name"] == "清晰增强"

    enhance_preview = client.get(enhance_json["result_url"])
    assert enhance_preview.status_code == 200
    with Image.open(io.BytesIO(enhance_preview.content)) as enhanced_image:
        assert enhanced_image.size == (960, 720)

    upload_path = storage_service.get_upload_path(file_id)
    if upload_path:
        storage_service.delete_path(upload_path)

    for task_id in (resize_task_id, enhance_task_id):
        task_detail = task_service.get_task(task_id)
        if task_detail:
            storage_service.delete_path(storage_service.get_result_path(task_id, task_detail.meta.format))
            storage_service.delete_path(task_service._task_path(task_id))

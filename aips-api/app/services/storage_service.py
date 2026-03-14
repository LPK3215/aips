from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import (
    ALLOWED_EXTENSIONS,
    MAX_UPLOAD_BYTES,
    RESULTS_DIR,
    TEMP_DIR,
    UPLOADS_DIR,
    ensure_storage_dirs,
)
from app.utils.ids import normalize_hex32


@dataclass
class UploadRecord:
    file_id: str
    path: Path
    size_bytes: int


class StorageService:
    def __init__(self) -> None:
        ensure_storage_dirs()
        self.uploads_dir = UPLOADS_DIR
        self.results_dir = RESULTS_DIR
        self.temp_dir = TEMP_DIR

    def _is_final_image_path(self, path: Path) -> bool:
        return path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS

    def _validate_extension(self, filename: str) -> str:
        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="仅支持 JPG、JPEG、PNG 格式。",
            )
        return extension

    def _validate_mime_type(self, content_type: str | None) -> None:
        allowed_mime_types = {"image/jpeg", "image/png", "image/jpg"}
        if content_type and content_type not in allowed_mime_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="仅支持 JPG、JPEG、PNG 格式的图像文件。",
            )

    def _allocate_upload_path(self, extension: str) -> tuple[str, Path, Path]:
        file_id = uuid4().hex
        target_path = self.uploads_dir / f"{file_id}{extension}"
        tmp_path = target_path.with_suffix(f"{target_path.suffix}.tmp")
        return file_id, target_path, tmp_path

    def save_upload(self, filename: str, content: bytes) -> UploadRecord:
        extension = self._validate_extension(filename)
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="上传文件不能超过 10MB。",
            )

        file_id, target_path, tmp_path = self._allocate_upload_path(extension)
        try:
            tmp_path.write_bytes(content)
            tmp_path.replace(target_path)
        except OSError as exc:
            tmp_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="上传文件保存失败，请稍后重试。",
            ) from exc
        return UploadRecord(file_id=file_id, path=target_path, size_bytes=len(content))

    async def save_upload_stream(self, upload: UploadFile) -> UploadRecord:
        filename = upload.filename or "upload.jpg"
        extension = self._validate_extension(filename)
        self._validate_mime_type(upload.content_type)
        file_id, target_path, tmp_path = self._allocate_upload_path(extension)
        size_bytes = 0

        try:
            with tmp_path.open("wb") as handle:
                while True:
                    chunk = await upload.read(1024 * 1024)
                    if not chunk:
                        break

                    size_bytes += len(chunk)
                    if size_bytes > MAX_UPLOAD_BYTES:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="上传文件不能超过 10MB。",
                        )

                    handle.write(chunk)

            tmp_path.replace(target_path)
        except HTTPException:
            tmp_path.unlink(missing_ok=True)
            raise
        except OSError as exc:
            tmp_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="上传文件保存失败，请稍后重试。",
            ) from exc

        return UploadRecord(file_id=file_id, path=target_path, size_bytes=size_bytes)

    def get_upload_path(self, file_id: str) -> Path | None:
        try:
            safe_id = normalize_hex32(file_id)
        except ValueError:
            return None

        matches = sorted(
            path for path in self.uploads_dir.glob(f"{safe_id}.*") if self._is_final_image_path(path)
        )
        return matches[0] if matches else None

    def get_result_path(self, task_id: str, output_format: str) -> Path:
        safe_id = normalize_hex32(task_id)
        extension = ".jpg" if output_format == "jpg" else ".png"
        return self.results_dir / f"{safe_id}{extension}"

    def create_temp_archive_path(self) -> Path:
        return self.temp_dir / f"{uuid4().hex}.zip.tmp"

    def delete_path(self, path: Path) -> None:
        if path.exists():
            path.unlink()

    def cleanup_uploads_before(self, cutoff_timestamp: float) -> int:
        deleted = 0
        for path in self.uploads_dir.iterdir():
            try:
                if not self._is_final_image_path(path):
                    continue
                if path.stat().st_mtime < cutoff_timestamp:
                    path.unlink(missing_ok=True)
                    deleted += 1
            except OSError:
                continue
        return deleted

    def cleanup_results_before(self, cutoff_timestamp: float) -> int:
        deleted = 0
        for path in self.results_dir.glob("*.*"):
            try:
                if path.stat().st_mtime < cutoff_timestamp:
                    path.unlink(missing_ok=True)
                    deleted += 1
            except OSError:
                continue
        return deleted


storage_service = StorageService()

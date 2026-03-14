const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
const MAX_BATCH_ITEMS = 20;
const ALLOWED_IMAGE_TYPES = new Set(["image/jpeg", "image/png"]);
const ALLOWED_EXTENSIONS = [".jpg", ".jpeg", ".png"];

function hasAllowedExtension(filename: string) {
  const lower = filename.toLowerCase();
  return ALLOWED_EXTENSIONS.some((extension) => lower.endsWith(extension));
}

export function validateImageFile(file: File): string | null {
  const type = file.type.trim().toLowerCase();
  if (type && !ALLOWED_IMAGE_TYPES.has(type)) {
    return "仅支持 JPG、JPEG、PNG 格式。";
  }

  if (!type && !hasAllowedExtension(file.name)) {
    return "仅支持 JPG、JPEG、PNG 格式。";
  }

  if (file.size > MAX_UPLOAD_BYTES) {
    return "上传文件不能超过 10MB。";
  }

  return null;
}

export function validateBatchImageFiles(files: File[]): string | null {
  if (files.length === 0) {
    return "请先选择要批量处理的图片。";
  }

  if (files.length > MAX_BATCH_ITEMS) {
    return `批量上传最多支持 ${MAX_BATCH_ITEMS} 张图片。`;
  }

  for (const file of files) {
    const error = validateImageFile(file);
    if (error) {
      return `${file.name}: ${error}`;
    }
  }

  return null;
}

export function buildZipDownloadName(filename: string | null | undefined, fallback = "id-photo-batch") {
  const source = (filename || fallback).trim() || fallback;
  const withoutZip = source.replace(/\.zip$/i, "").trim();
  return `${withoutZip || fallback}.zip`;
}

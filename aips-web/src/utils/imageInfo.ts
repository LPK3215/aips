function greatestCommonDivisor(a: number, b: number): number {
  let left = Math.abs(Math.round(a));
  let right = Math.abs(Math.round(b));

  while (right !== 0) {
    const remainder = left % right;
    left = right;
    right = remainder;
  }

  return left || 1;
}

function formatRounded(value: number, digits: number): string {
  return Number(value.toFixed(digits)).toString();
}

export function formatFileSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return "0 KB";
  }

  if (bytes >= 1024 * 1024) {
    return `${formatRounded(bytes / (1024 * 1024), bytes >= 10 * 1024 * 1024 ? 1 : 2)} MB`;
  }

  return `${formatRounded(bytes / 1024, bytes >= 100 * 1024 ? 0 : 1)} KB`;
}

export function formatKilobytes(kilobytes: number): string {
  if (!Number.isFinite(kilobytes) || kilobytes <= 0) {
    return "0 KB";
  }

  if (kilobytes >= 1024) {
    return `${formatRounded(kilobytes / 1024, kilobytes >= 10 * 1024 ? 1 : 2)} MB`;
  }

  return `${formatRounded(kilobytes, kilobytes >= 100 ? 0 : 1)} KB`;
}

export function formatPixelSize(width: number, height: number): string {
  return `${width} x ${height} px`;
}

export function formatAspectRatio(width: number, height: number): string {
  if (!width || !height) {
    return "-";
  }

  const divisor = greatestCommonDivisor(width, height);
  return `${Math.round(width / divisor)}:${Math.round(height / divisor)}`;
}

export function formatMegapixels(width: number, height: number): string {
  if (!width || !height) {
    return "-";
  }

  const megapixels = (width * height) / 1_000_000;
  return `${formatRounded(megapixels, megapixels >= 1 ? 2 : 3)} MP`;
}

export function formatOrientation(width: number, height: number): string {
  if (!width || !height) {
    return "-";
  }

  if (width === height) {
    return "方图";
  }

  return width > height ? "横图" : "竖图";
}

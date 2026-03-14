import type { SizeFormState } from "../types";


export const MAX_OUTPUT_PIXELS = 25_000_000;

function formatRounded(value: number, digits: number) {
  return Number(value.toFixed(digits)).toString();
}

function toPositiveNumber(value: unknown, fallback = 0) {
  const raw = typeof value === "number" ? value : Number(value);
  return Number.isFinite(raw) && raw > 0 ? raw : fallback;
}

export function resolveOutputPixels(size: Pick<SizeFormState, "width" | "height" | "unit" | "dpi">) {
  const width = toPositiveNumber(size.width);
  const height = toPositiveNumber(size.height);
  const dpi = toPositiveNumber(size.dpi, 300);

  if (size.unit === "px") {
    return {
      width: Math.max(1, Math.round(width)),
      height: Math.max(1, Math.round(height)),
    };
  }

  const inchFactor =
    size.unit === "cm"
      ? 1 / 2.54
      : size.unit === "mm"
        ? 1 / 25.4
        : 1;

  return {
    width: Math.max(1, Math.round(width * inchFactor * dpi)),
    height: Math.max(1, Math.round(height * inchFactor * dpi)),
  };
}

export function isOutputPixelLimitExceeded(width: number, height: number) {
  return width > 0 && height > 0 && width * height > MAX_OUTPUT_PIXELS;
}

export function formatMegapixelCount(width: number, height: number) {
  if (!width || !height) {
    return "0 MP";
  }

  const megapixels = (width * height) / 1_000_000;
  return `${formatRounded(megapixels, megapixels >= 1 ? 2 : 3)} MP`;
}

export function buildOutputLimitHint(
  width: number,
  height: number,
  label = "当前输出",
) {
  return `${label}约 ${width} x ${height} px（${formatMegapixelCount(width, height)}），超过 25MP 安全上限。请降低尺寸、DPI 或放大倍率。`;
}

import type {
  AdjustmentState,
  BasicOutputState,
  EnhanceToolState,
  OutputState,
  RenderState,
  ResizeToolState,
  SizeFormState,
} from "../types";


function roundNumber(value: number, digits = 4) {
  return Number(value.toFixed(digits));
}

function normalizeSize(size: SizeFormState) {
  return {
    width: roundNumber(Number(size.width) || 0),
    height: roundNumber(Number(size.height) || 0),
    unit: size.unit,
    dpi: Number(size.dpi) || 0,
  };
}

function normalizeRender(render: RenderState) {
  return {
    viewport_width: roundNumber(Number(render.viewport_width) || 0),
    viewport_height: roundNumber(Number(render.viewport_height) || 0),
    scale: roundNumber(Number(render.scale) || 0, 6),
    offset_x: roundNumber(Number(render.offset_x) || 0, 2),
    offset_y: roundNumber(Number(render.offset_y) || 0, 2),
    fit_mode: render.fit_mode,
  };
}

function normalizeAdjustments(adjustments: AdjustmentState) {
  return {
    brightness: Number(adjustments.brightness) || 0,
    contrast: Number(adjustments.contrast) || 0,
    saturation: Number(adjustments.saturation) || 0,
    sharpness: Number(adjustments.sharpness) || 0,
    blur: Number(adjustments.blur) || 0,
  };
}

function normalizeOutput(output: OutputState) {
  return {
    format: output.format,
    dpi: Number(output.dpi) || 0,
    quality: Number(output.quality) || 0,
    target_size_kb_min: output.target_size_kb_min ?? null,
    target_size_kb_max: output.target_size_kb_max ?? null,
    filename: output.filename,
    background_color: output.background_color,
    replace_background: output.replace_background,
    replace_feather: Number(output.replace_feather) || 0,
  };
}

function normalizeBasicOutput(output: BasicOutputState) {
  return {
    format: output.format,
    dpi: Number(output.dpi) || 0,
    quality: Number(output.quality) || 0,
    filename: output.filename,
    background_color: output.background_color,
  };
}

export function createWorkbenchSignature(payload: {
  fileId: string | null;
  presetId: string | null;
  size: SizeFormState;
  render: RenderState;
  adjustments: AdjustmentState;
  output: OutputState;
}) {
  return JSON.stringify({
    file_id: payload.fileId,
    preset_id: payload.presetId,
    size: normalizeSize(payload.size),
    render: normalizeRender(payload.render),
    adjustments: normalizeAdjustments(payload.adjustments),
    output: normalizeOutput(payload.output),
  });
}

export function createBatchSignature(payload: {
  fileIds: string[];
  presetId: string | null;
  size: SizeFormState;
  viewportWidth: number;
  viewportHeight: number;
  fitMode: "fill" | "fit";
  adjustments: AdjustmentState;
  output: OutputState;
}) {
  return JSON.stringify({
    file_ids: [...payload.fileIds].sort(),
    preset_id: payload.presetId,
    size: normalizeSize(payload.size),
    viewport_width: roundNumber(payload.viewportWidth),
    viewport_height: roundNumber(payload.viewportHeight),
    fit_mode: payload.fitMode,
    adjustments: normalizeAdjustments(payload.adjustments),
    output: normalizeOutput(payload.output),
  });
}

export function createResizeSignature(payload: {
  fileId: string | null;
  resize: ResizeToolState;
  output: BasicOutputState;
}) {
  return JSON.stringify({
    file_id: payload.fileId,
    width_px: roundNumber(Number(payload.resize.width_px) || 0),
    height_px: roundNumber(Number(payload.resize.height_px) || 0),
    output: normalizeBasicOutput(payload.output),
  });
}

export function createEnhanceSignature(payload: {
  fileId: string | null;
  enhance: EnhanceToolState;
  output: BasicOutputState;
}) {
  return JSON.stringify({
    file_id: payload.fileId,
    scale_factor: roundNumber(Number(payload.enhance.scale_factor) || 0, 3),
    denoise: Number(payload.enhance.denoise) || 0,
    sharpness: Number(payload.enhance.sharpness) || 0,
    contrast: Number(payload.enhance.contrast) || 0,
    auto_contrast: payload.enhance.auto_contrast,
    output: normalizeBasicOutput(payload.output),
  });
}

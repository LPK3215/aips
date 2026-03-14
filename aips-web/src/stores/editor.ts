import { defineStore } from "pinia";

import type {
  AdjustmentState,
  FitMode,
  OutputState,
  PresetItem,
  ProcessRequestPayload,
  ProcessResponse,
  RenderState,
  SizeFormState,
  SizeUnit,
  TaskSummaryResponse,
  UploadResponse,
} from "../types";


interface RestoredTaskDraft {
  taskId: string;
  presetName: string | null;
}

const defaultAdjustments = (): AdjustmentState => ({
  brightness: 0,
  contrast: 0,
  saturation: 0,
  sharpness: 18,
  blur: 0,
});

const defaultSize = (): SizeFormState => ({
  width: 3.5,
  height: 5.3,
  unit: "cm",
  dpi: 300,
});

const defaultOutput = (): OutputState => ({
  format: "jpg",
  dpi: 300,
  quality: 90,
  target_size_kb_min: 100,
  target_size_kb_max: 200,
  filename: "id-photo-result",
  background_color: "#ffffff",
  replace_background: false,
  replace_feather: 6,
});

const defaultRender = (): RenderState => ({
  viewport_width: 320,
  viewport_height: 486,
  scale: 0.3,
  offset_x: 0,
  offset_y: 0,
  fit_mode: "fill",
});

function revokeBlobUrl(url: string) {
  if (url.startsWith("blob:")) {
    URL.revokeObjectURL(url);
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function normalizeNumber(value: unknown, fallback: number, bounds?: { min?: number; max?: number }) {
  const raw = typeof value === "number" ? value : typeof value === "string" ? Number(value) : Number.NaN;
  if (!Number.isFinite(raw)) {
    return fallback;
  }

  let next = raw;
  if (typeof bounds?.min === "number") {
    next = Math.max(bounds.min, next);
  }
  if (typeof bounds?.max === "number") {
    next = Math.min(bounds.max, next);
  }
  return next;
}

function normalizeNullableNumber(value: unknown, bounds?: { min?: number; max?: number }) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const raw = typeof value === "number" ? value : typeof value === "string" ? Number(value) : Number.NaN;
  if (!Number.isFinite(raw)) {
    return null;
  }

  let next = raw;
  if (typeof bounds?.min === "number") {
    next = Math.max(bounds.min, next);
  }
  if (typeof bounds?.max === "number") {
    next = Math.min(bounds.max, next);
  }
  return next;
}

function normalizeString(value: unknown, fallback: string) {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function normalizeNullableString(value: unknown) {
  return typeof value === "string" && value.trim() ? value : null;
}

function normalizeBoolean(value: unknown, fallback: boolean) {
  return typeof value === "boolean" ? value : fallback;
}

function normalizeSizeUnit(value: unknown, fallback: SizeUnit): SizeUnit {
  return value === "px" || value === "mm" || value === "cm" || value === "inch" ? value : fallback;
}

function normalizeFitMode(value: unknown, fallback: FitMode): FitMode {
  return value === "fit" || value === "fill" ? value : fallback;
}

function normalizeOutputFormat(value: unknown, fallback: OutputState["format"]): OutputState["format"] {
  return value === "png" || value === "jpg" ? value : fallback;
}

function normalizeHexColor(value: unknown, fallback: string) {
  return typeof value === "string" && /^#([0-9a-fA-F]{6})$/.test(value) ? value : fallback;
}

function normalizeProcessPayload(payload: unknown): ProcessRequestPayload | null {
  if (!isRecord(payload)) {
    return null;
  }

  const customSize = isRecord(payload.custom_size) ? payload.custom_size : null;
  const render = isRecord(payload.render) ? payload.render : null;
  const adjustments = isRecord(payload.adjustments) ? payload.adjustments : null;
  const output = isRecord(payload.output) ? payload.output : null;
  const fileId = normalizeString(payload.file_id, "");

  if (!customSize || !render || !adjustments || !output || !fileId) {
    return null;
  }

  const sizeDefaults = defaultSize();
  const adjustmentDefaults = defaultAdjustments();
  const outputDefaults = defaultOutput();
  const renderDefaults = defaultRender();
  const targetSizeMin = normalizeNullableNumber(output.target_size_kb_min, { min: 1, max: 10000 });
  const targetSizeMax = normalizeNullableNumber(output.target_size_kb_max, { min: 1, max: 10000 });

  return {
    file_id: fileId,
    preset_id: normalizeNullableString(payload.preset_id),
    custom_size: {
      width: normalizeNumber(customSize.width, sizeDefaults.width, { min: 0.1 }),
      height: normalizeNumber(customSize.height, sizeDefaults.height, { min: 0.1 }),
      unit: normalizeSizeUnit(customSize.unit, sizeDefaults.unit),
      dpi: normalizeNumber(customSize.dpi, sizeDefaults.dpi, { min: 72, max: 600 }),
    },
    render: {
      viewport_width: normalizeNumber(render.viewport_width, renderDefaults.viewport_width, { min: 1 }),
      viewport_height: normalizeNumber(render.viewport_height, renderDefaults.viewport_height, { min: 1 }),
      scale: normalizeNumber(render.scale, renderDefaults.scale, { min: 0.01 }),
      offset_x: normalizeNumber(render.offset_x, renderDefaults.offset_x),
      offset_y: normalizeNumber(render.offset_y, renderDefaults.offset_y),
      fit_mode: normalizeFitMode(render.fit_mode, renderDefaults.fit_mode),
    },
    adjustments: {
      brightness: normalizeNumber(adjustments.brightness, adjustmentDefaults.brightness, { min: -100, max: 100 }),
      contrast: normalizeNumber(adjustments.contrast, adjustmentDefaults.contrast, { min: -100, max: 100 }),
      saturation: normalizeNumber(adjustments.saturation, adjustmentDefaults.saturation, { min: -100, max: 100 }),
      sharpness: normalizeNumber(adjustments.sharpness, adjustmentDefaults.sharpness, { min: 0, max: 100 }),
      blur: normalizeNumber(adjustments.blur, adjustmentDefaults.blur, { min: 0, max: 20 }),
    },
    output: {
      format: normalizeOutputFormat(output.format, outputDefaults.format),
      dpi: normalizeNumber(output.dpi, outputDefaults.dpi, { min: 72, max: 600 }),
      quality: normalizeNumber(output.quality, outputDefaults.quality, { min: 35, max: 100 }),
      target_size_kb_min:
        targetSizeMin !== null && targetSizeMax !== null && targetSizeMin > targetSizeMax ? targetSizeMax : targetSizeMin,
      target_size_kb_max:
        targetSizeMin !== null && targetSizeMax !== null && targetSizeMin > targetSizeMax ? targetSizeMin : targetSizeMax,
      filename: normalizeString(output.filename, outputDefaults.filename),
      background_color: normalizeHexColor(output.background_color, outputDefaults.background_color),
      replace_background: normalizeBoolean(output.replace_background, outputDefaults.replace_background),
      replace_feather: normalizeNumber(output.replace_feather, outputDefaults.replace_feather, { min: 0, max: 24 }),
    },
  };
}

export const useEditorStore = defineStore("editor", {
  state: () => ({
    presets: [] as PresetItem[],
    selectedPresetId: null as string | null,
    upload: null as UploadResponse | null,
    sourceUrl: "" as string,
    size: defaultSize(),
    adjustments: defaultAdjustments(),
    output: defaultOutput(),
    render: defaultRender(),
    lastProcess: null as ProcessResponse | null,
    lastProcessSignature: "" as string,
    recentTasks: [] as TaskSummaryResponse[],
    recentTasksMissingCount: 0,
    restoredTaskDraft: null as RestoredTaskDraft | null,
  }),
  actions: {
    setPresets(items: PresetItem[]) {
      this.presets = items;
      if (!this.selectedPresetId && !this.restoredTaskDraft && items.length > 0) {
        this.applyPreset(items[0]);
      }
    },
    clearUploadedSource() {
      revokeBlobUrl(this.sourceUrl);
      this.upload = null;
      this.sourceUrl = "";
      this.lastProcessSignature = "";
    },
    setUploadedSource(payload: { upload: UploadResponse; sourceUrl: string }) {
      this.clearUploadedSource();
      this.upload = payload.upload;
      this.sourceUrl = payload.sourceUrl;
      this.lastProcess = null;
      this.lastProcessSignature = "";
      this.restoredTaskDraft = null;
    },
    applyPreset(preset: PresetItem) {
      this.selectedPresetId = preset.id;
      this.size = {
        width: preset.width,
        height: preset.height,
        unit: preset.unit,
        dpi: preset.dpi,
      };
      this.output = {
        ...this.output,
        format: preset.format,
        dpi: preset.dpi,
        target_size_kb_min: preset.target_size_kb_min,
        target_size_kb_max: preset.target_size_kb_max,
        background_color: preset.background_color,
        filename: preset.name,
      };
    },
    setRender(render: RenderState) {
      this.render = render;
    },
    setFitMode(fitMode: FitMode) {
      this.render = {
        ...this.render,
        fit_mode: fitMode,
      };
    },
    setRecentTasks(items: TaskSummaryResponse[], missingCount = 0) {
      this.recentTasks = items;
      this.recentTasksMissingCount = missingCount;
    },
    clearRestoredTaskDraft() {
      this.restoredTaskDraft = null;
    },
    restoreFromTaskParams(taskId: string, params: unknown, presetName: string | null = null) {
      const normalized = normalizeProcessPayload(params);
      if (!normalized) {
        return false;
      }

      this.clearUploadedSource();
      this.selectedPresetId = normalized.preset_id;
      this.size = normalized.custom_size;
      this.adjustments = normalized.adjustments;
      this.output = normalized.output;
      this.render = normalized.render;
      this.lastProcess = null;
      this.lastProcessSignature = "";
      this.restoredTaskDraft = {
        taskId,
        presetName,
      };
      return true;
    },
  },
});

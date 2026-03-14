export type SizeUnit = "px" | "mm" | "cm" | "inch";
export type FitMode = "fill" | "fit";
export type OutputFormat = "jpg" | "png";

export interface PresetItem {
  id: string;
  name: string;
  category: string;
  width: number;
  height: number;
  unit: SizeUnit;
  dpi: number;
  format: OutputFormat;
  target_size_kb_min: number | null;
  target_size_kb_max: number | null;
  background_color: string;
  description: string;
}

export interface PresetCollectionResponse {
  items: PresetItem[];
  categories: string[];
}

export interface UploadResponse {
  file_id: string;
  width_px: number;
  height_px: number;
  size_bytes: number;
  format: string;
  original_filename: string;
}

export interface UploadBatchItem {
  index: number;
  ok: boolean;
  upload: UploadResponse | null;
  error: string | null;
}

export interface UploadBatchResponse {
  items: UploadBatchItem[];
}

export interface RenderState {
  viewport_width: number;
  viewport_height: number;
  scale: number;
  offset_x: number;
  offset_y: number;
  fit_mode: FitMode;
}

export interface SizeFormState {
  width: number;
  height: number;
  unit: SizeUnit;
  dpi: number;
}

export interface AdjustmentState {
  brightness: number;
  contrast: number;
  saturation: number;
  sharpness: number;
  blur: number;
}

export interface OutputState {
  format: OutputFormat;
  dpi: number;
  quality: number;
  target_size_kb_min: number | null;
  target_size_kb_max: number | null;
  filename: string;
  background_color: string;
  background_image_id: string | null;
  replace_background: boolean;
  replace_feather: number;
}

export interface BasicOutputState {
  format: OutputFormat;
  dpi: number;
  quality: number;
  filename: string;
  background_color: string;
}

export interface ResizeToolState {
  width_px: number;
  height_px: number;
}

export interface EnhanceToolState {
  scale_factor: number;
  denoise: number;
  sharpness: number;
  contrast: number;
  auto_contrast: boolean;
}

export interface ProcessRequestPayload {
  file_id: string;
  preset_id: string | null;
  custom_size: SizeFormState;
  render: RenderState;
  adjustments: AdjustmentState;
  output: OutputState;
}

export interface ResultMeta {
  width_px: number;
  height_px: number;
  format: OutputFormat;
  dpi: number;
  size_kb: number;
  filename: string;
  background_color: string;
  preset_name?: string | null;
}

export interface TaskSubmissionResponse {
  task_id: string;
  result_url: string;
  download_url: string;
  meta: ResultMeta | null;
}

export interface ProcessResponse {
  task_id: string;
  result_url: string;
  download_url: string;
  meta: ResultMeta;
}

export interface TaskStatusResponse {
  task_id: string;
  status: string;
  progress: number;
  message: string;
}

export interface BatchProcessItemResult {
  index: number;
  ok: boolean;
  task_id: string | null;
  result_url: string | null;
  download_url: string | null;
  meta: ResultMeta | null;
  error: string | null;
}

export interface BatchProcessResponse {
  items: BatchProcessItemResult[];
}

export interface TaskDetailResponse {
  task_id: string;
  result_url: string;
  download_url: string;
  file_available: boolean;
  created_at: string;
  meta: ResultMeta;
  params?: ProcessRequestPayload | null;
}

export interface TaskSummaryResponse {
  task_id: string;
  result_url: string;
  download_url: string;
  file_available: boolean;
  created_at: string;
  meta: ResultMeta;
}

export interface TaskListResponse {
  items: TaskSummaryResponse[];
  missing_count: number;
}

export interface FaceBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface SuggestRenderResponse {
  render: RenderState;
  face_box: FaceBox | null;
  note: string;
}

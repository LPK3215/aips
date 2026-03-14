import type {
  BasicOutputState,
  BatchProcessResponse,
  EnhanceToolState,
  PresetCollectionResponse,
  ProcessRequestPayload,
  ProcessResponse,
  RenderState,
  ResizeToolState,
  SizeFormState,
  AdjustmentState,
  OutputState,
  SuggestRenderResponse,
  TaskDetailResponse,
  TaskListResponse,
  UploadBatchResponse,
  UploadResponse,
} from "../types";


const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  status: number;
  requestId: string | null;
  retryAfterSeconds: number | null;

  constructor(
    message: string,
    options: {
      status: number;
      requestId?: string | null;
      retryAfterSeconds?: number | null;
    },
  ) {
    super(message);
    this.name = "ApiError";
    this.status = options.status;
    this.requestId = options.requestId ?? null;
    this.retryAfterSeconds = options.retryAfterSeconds ?? null;
  }
}

function readRetryAfter(response: Response): number | null {
  const header = response.headers.get("Retry-After");
  if (!header) {
    return null;
  }

  const seconds = Number(header);
  return Number.isFinite(seconds) && seconds > 0 ? seconds : null;
}

async function unwrap<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new ApiError(payload?.detail ?? "请求失败。", {
      status: response.status,
      requestId: response.headers.get("X-Request-ID"),
      retryAfterSeconds: readRetryAfter(response),
    });
  }

  return (await response.json()) as T;
}

export function formatApiError(error: unknown, fallback: string): string {
  if (!(error instanceof ApiError)) {
    return error instanceof Error ? error.message : fallback;
  }

  let message = error.message || fallback;
  if (error.status === 429 && error.retryAfterSeconds && !message.includes("秒后重试")) {
    message = `${message}（建议 ${error.retryAfterSeconds} 秒后重试）`;
  }
  if (error.requestId && error.status >= 429) {
    message = `${message} [请求ID ${error.requestId}]`;
  }
  return message;
}

export function getRetryAfterSeconds(error: unknown): number | null {
  return error instanceof ApiError ? error.retryAfterSeconds : null;
}

export async function fetchPresets(): Promise<PresetCollectionResponse> {
  const response = await fetch(`${apiBase}/api/v1/presets`);
  return unwrap<PresetCollectionResponse>(response);
}

export async function uploadImage(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${apiBase}/api/v1/files/upload`, {
    method: "POST",
    body: formData,
  });

  return unwrap<UploadResponse>(response);
}

export async function uploadImagesBatch(files: File[]): Promise<UploadBatchResponse> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  const response = await fetch(`${apiBase}/api/v1/files/upload-batch`, {
    method: "POST",
    body: formData,
  });

  return unwrap<UploadBatchResponse>(response);
}

export async function processImage(payload: ProcessRequestPayload): Promise<ProcessResponse> {
  const response = await fetch(`${apiBase}/api/v1/images/process`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return unwrap<ProcessResponse>(response);
}

export async function processBatchAuto(payload: {
  file_ids: string[];
  preset_id: string | null;
  custom_size: SizeFormState;
  viewport_width: number;
  viewport_height: number;
  fit_mode: "fill" | "fit";
  anchor_y?: number;
  face_height_ratio?: number;
  adjustments: AdjustmentState;
  output: OutputState;
}): Promise<BatchProcessResponse> {
  const response = await fetch(`${apiBase}/api/v1/images/process-batch-auto`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return unwrap<BatchProcessResponse>(response);
}

export async function fetchTask(taskId: string): Promise<TaskDetailResponse> {
  const response = await fetch(`${apiBase}/api/v1/tasks/${taskId}`);
  return unwrap<TaskDetailResponse>(response);
}

export async function fetchRecentTasks(limit = 12): Promise<TaskListResponse> {
  const response = await fetch(`${apiBase}/api/v1/tasks?limit=${limit}`);
  return unwrap<TaskListResponse>(response);
}

export async function suggestRender(payload: {
  file_id: string;
  custom_size: SizeFormState;
  viewport_width: number;
  viewport_height: number;
  fit_mode: "fill" | "fit";
  anchor_y?: number;
  face_height_ratio?: number;
}): Promise<SuggestRenderResponse> {
  const response = await fetch(`${apiBase}/api/v1/images/suggest-render`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return unwrap<SuggestRenderResponse>(response);
}

export function buildApiUrl(relativePath: string): string {
  return `${apiBase}${relativePath}`;
}

export async function composeSheet(payload: {
  task_id: string;
  page_size: SizeFormState;
  margin_mm?: number;
  gap_mm?: number;
  cols?: number | null;
  rows?: number | null;
  copies?: number | null;
  show_cut_lines?: boolean;
  cut_line_color?: string;
  cut_line_width?: number;
  output: {
    format: "jpg" | "png";
    dpi: number;
    quality: number;
    filename?: string | null;
    background_color: string;
  };
}): Promise<ProcessResponse> {
  const response = await fetch(`${apiBase}/api/v1/images/compose-sheet`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return unwrap<ProcessResponse>(response);
}

export async function downloadZipArchive(payload: {
  task_ids: string[];
  filename?: string;
  include_manifest?: boolean;
}): Promise<Blob> {
  const response = await fetch(`${apiBase}/api/v1/files/download-zip`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new ApiError(data?.detail ?? "下载失败。", {
      status: response.status,
      requestId: response.headers.get("X-Request-ID"),
      retryAfterSeconds: readRetryAfter(response),
    });
  }

  return response.blob();
}

export async function resizeImageTool(payload: {
  file_id: string;
  width_px: ResizeToolState["width_px"];
  height_px: ResizeToolState["height_px"];
  output: BasicOutputState;
}): Promise<ProcessResponse> {
  const response = await fetch(`${apiBase}/api/v1/images/resize`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return unwrap<ProcessResponse>(response);
}

export async function enhanceImageTool(payload: {
  file_id: string;
  scale_factor: EnhanceToolState["scale_factor"];
  denoise: EnhanceToolState["denoise"];
  sharpness: EnhanceToolState["sharpness"];
  contrast: EnhanceToolState["contrast"];
  auto_contrast: EnhanceToolState["auto_contrast"];
  output: BasicOutputState;
}): Promise<ProcessResponse> {
  const response = await fetch(`${apiBase}/api/v1/images/enhance`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return unwrap<ProcessResponse>(response);
}

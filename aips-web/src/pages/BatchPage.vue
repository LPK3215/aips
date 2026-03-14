<template>
  <main class="app-shell">
    <AppTopNav />

    <section class="hero hero--compact">
      <div class="hero__copy">
        <p class="eyebrow">BATCH EXPORT</p>
        <h1>批量自动居中，一次性导出。</h1>
        <p class="hero__lede">
          适合已经“基本构图正确”的多张照片。系统会对每张图自动检测人脸并生成构图建议，然后按同一规格与参数真实导出。
        </p>
      </div>
      <div class="hero__badge">
        <span>统一规格</span>
        <span>批量构图建议</span>
        <RouterLink class="button button--secondary" to="/">返回工作台</RouterLink>
      </div>
    </section>

    <section class="workspace-grid">
      <div class="workspace-grid__left">
        <BatchDropzone :files="selectedFiles" @select="handleSelectFiles" @clear="clearSelection" />
        <EditorSectionSwitcher v-model="activeSection" :sections="operationSections" />
        <PresetSelector
          v-show="activeSection === 'presets'"
          :presets="presets"
          :selected-id="selectedPresetId"
          @select="applyPreset"
        />
        <SizeForm v-show="activeSection === 'size'" v-model="size" />
        <OutputSettings v-show="activeSection === 'output'" v-model="output" />
        <AdjustmentPanel v-show="activeSection === 'adjustments'" v-model="adjustments" v-model:fit-mode="fitMode" />
      </div>

      <div class="workspace-grid__right">
        <section class="panel">
          <div class="panel__header">
            <div>
              <p class="eyebrow">Run</p>
              <h3>批量导出</h3>
            </div>
          </div>

          <div class="workflow-card">
            <p class="workflow-card__label">使用顺序</p>
            <WorkflowSteps :steps="workflowSteps" />
            <div class="workflow-callout" :class="`workflow-callout--${workflowTone}`">
              <strong>{{ workflowTitle }}</strong>
              <p>{{ workflowMessage }}</p>
            </div>
          </div>

          <div class="status-stack">
            <div class="status-card">
              <strong>已上传</strong>
              <p>{{ successfulUploads.length }} / {{ uploadItems.length }}</p>
            </div>
            <div class="status-card">
              <strong>构图</strong>
              <p>{{ fitMode === "fill" ? "填充裁切" : "完整适配" }} · {{ viewportWidth }} x {{ viewportHeight }}</p>
            </div>
            <div class="status-card">
              <strong>结果状态</strong>
              <p v-if="outputLimitExceeded">尺寸超限</p>
              <p v-else>{{ resultsStatusText }}</p>
            </div>
          </div>

          <p v-if="outputLimitExceeded" class="error-text panel__hint panel__hint--compact">{{ outputLimitMessage }}</p>
          <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
          <p v-if="retryCooldown.isCoolingDown.value" class="panel__hint panel__hint--compact">
            限流保护中，{{ retryCooldown.secondsRemaining.value }} 秒后可再次发起批量操作。
          </p>

          <div class="action-row">
            <button
              class="button button--primary"
              type="button"
              :disabled="!canProcess || uploading || processing || retryCooldown.isCoolingDown.value"
              @click="handleBatchProcess"
            >
              {{
                uploading
                  ? "上传中..."
                  : processing
                    ? "处理中..."
                    : retryCooldown.isCoolingDown.value
                      ? `${retryCooldown.secondsRemaining.value} 秒后重试`
                      : batchProcessButtonLabel
              }}
            </button>
            <button
              v-if="results.length"
              class="button button--secondary"
              type="button"
              @click="clearResults"
            >
              清空结果
            </button>
          </div>
        </section>

        <section v-if="uploadItems.length" class="panel">
          <div class="panel__header">
            <div>
              <p class="eyebrow">Uploads</p>
              <h3>上传状态</h3>
            </div>
          </div>
          <div class="batch-status">
            <div v-for="item in uploadItems" :key="item.index" class="batch-status__item">
              <span class="batch-status__index">{{ item.index + 1 }}</span>
              <div class="batch-status__meta">
                <strong>{{ item.name }}</strong>
                <small v-if="item.upload">
                  {{ item.upload.width_px }} x {{ item.upload.height_px }} · {{ Math.round(item.upload.size_bytes / 1024) }} KB
                </small>
                <small v-else class="error-text">{{ item.error }}</small>
              </div>
            </div>
          </div>
        </section>

        <section v-if="results.length" class="panel">
          <div class="panel__header">
            <div>
              <p class="eyebrow">Results</p>
              <h3>{{ resultsOutdated ? "上一次导出结果" : "导出结果" }}</h3>
            </div>
            <div class="panel__actions">
              <button
                v-if="okTaskIds.length"
                class="chip"
                type="button"
                :disabled="downloading"
                @click="handleDownloadAll"
              >
                {{ downloading ? "打包中..." : downloadZipLabel }}
              </button>
              <small>{{ results.length }} 条</small>
            </div>
          </div>

          <p v-if="resultsOutdated" class="panel__hint panel__hint--compact">
            你已经修改了批量参数，下面这些结果是按旧参数生成的。建议重新批量导出后再统一下载。
          </p>

          <div class="batch-results">
            <div v-for="item in results" :key="item.index" class="batch-result">
              <div class="batch-result__row">
                <strong>#{{ item.original_index + 1 }} · {{ item.name }}</strong>
                <small v-if="item.ok && item.meta">{{ item.meta.size_kb }} KB</small>
                <small v-else class="error-text">{{ item.error }}</small>
              </div>
              <div v-if="item.ok && item.task_id" class="batch-result__actions">
                <RouterLink class="button button--secondary" :to="`/result/${item.task_id}`">查看</RouterLink>
                <a class="button button--primary" :href="buildApiUrl(item.download_url || '')" download>下载</a>
              </div>
            </div>
          </div>
        </section>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import {
  fetchPresets,
  processBatchAuto,
  uploadImagesBatch,
  buildApiUrl,
  downloadZipArchive,
  formatApiError,
  getRetryAfterSeconds,
} from "../api/client";
import AdjustmentPanel from "../components/AdjustmentPanel.vue";
import AppTopNav from "../components/AppTopNav.vue";
import BatchDropzone from "../components/BatchDropzone.vue";
import EditorSectionSwitcher from "../components/EditorSectionSwitcher.vue";
import OutputSettings from "../components/OutputSettings.vue";
import PresetSelector from "../components/PresetSelector.vue";
import SizeForm from "../components/SizeForm.vue";
import WorkflowSteps from "../components/WorkflowSteps.vue";
import { useRetryCooldown } from "../composables/useRetryCooldown";
import type { AdjustmentState, BatchProcessItemResult, FitMode, OutputState, PresetItem, SizeFormState, UploadResponse } from "../types";
import { buildOutputLimitHint, isOutputPixelLimitExceeded, resolveOutputPixels } from "../utils/outputSafety";
import { createBatchSignature } from "../utils/requestSignature";
import { buildZipDownloadName, validateBatchImageFiles } from "../utils/uploadValidation";


const presets = ref<PresetItem[]>([]);
const selectedPresetId = ref<string | null>(null);
const selectedFiles = ref<File[]>([]);
const activeSection = ref("presets");

const uploading = ref(false);
const processing = ref(false);
const downloading = ref(false);
const errorMessage = ref("");
const lastBatchSignature = ref("");
const retryCooldown = useRetryCooldown();

const size = ref<SizeFormState>({
  width: 3.5,
  height: 5.3,
  unit: "cm",
  dpi: 300,
});

const adjustments = ref<AdjustmentState>({
  brightness: 0,
  contrast: 0,
  saturation: 0,
  sharpness: 18,
  blur: 0,
});

const output = ref<OutputState>({
  format: "jpg",
  dpi: 300,
  quality: 90,
  target_size_kb_min: 100,
  target_size_kb_max: 200,
  filename: "id-photo-batch",
  background_color: "#ffffff",
  replace_background: false,
  replace_feather: 6,
});

const fitMode = ref<FitMode>("fill");

type UploadItemState = {
  index: number;
  name: string;
  upload: UploadResponse | null;
  error: string | null;
};

const uploadItems = ref<UploadItemState[]>([]);
type BatchResultView = BatchProcessItemResult & { name: string; original_index: number };
const results = ref<BatchResultView[]>([]);

const successfulUploads = computed(() => uploadItems.value.filter((item) => Boolean(item.upload)));
const okTaskIds = computed(() =>
  results.value
    .filter((item) => item.ok && Boolean(item.task_id))
    .map((item) => String(item.task_id)),
);

const ratio = computed(() => {
  const w = Number(size.value.width) || 1;
  const h = Number(size.value.height) || 1;
  return w / h;
});

const viewportWidth = computed(() => 320);
const viewportHeight = computed(() => Math.max(220, Math.round(viewportWidth.value / ratio.value)));

const resolvedOutputPixels = computed(() => resolveOutputPixels(size.value));
const outputLimitExceeded = computed(() =>
  isOutputPixelLimitExceeded(resolvedOutputPixels.value.width, resolvedOutputPixels.value.height),
);
const outputLimitMessage = computed(() =>
  buildOutputLimitHint(resolvedOutputPixels.value.width, resolvedOutputPixels.value.height, "批量导出"),
);
const canProcess = computed(() => successfulUploads.value.length > 0 && !outputLimitExceeded.value);
const currentBatchSignature = computed(() =>
  createBatchSignature({
    fileIds: successfulUploads.value.map((item) => item.upload?.file_id ?? "").filter(Boolean),
    presetId: selectedPresetId.value,
    size: size.value,
    viewportWidth: viewportWidth.value,
    viewportHeight: viewportHeight.value,
    fitMode: fitMode.value,
    adjustments: adjustments.value,
    output: output.value,
  }),
);
const resultsOutdated = computed(
  () => Boolean(results.value.length && lastBatchSignature.value && currentBatchSignature.value !== lastBatchSignature.value),
);
const batchProcessButtonLabel = computed(() => {
  if (resultsOutdated.value) {
    return "按新参数重新批量导出";
  }

  return results.value.length ? "重新批量导出" : "自动居中并批量导出";
});
const resultsStatusText = computed(() => {
  if (!results.value.length) {
    return "还没有结果";
  }

  return resultsOutdated.value ? "结果待更新" : "结果已同步";
});
const downloadZipLabel = computed(() => (resultsOutdated.value ? "下载旧结果 ZIP" : "下载 ZIP"));
const workflowSteps = computed(() => {
  if (!selectedFiles.value.length) {
    return [
      { index: 1, label: "批量上传", status: "current" as const },
      { index: 2, label: "检查上传", status: "pending" as const },
      { index: 3, label: "批量导出", status: "pending" as const },
      { index: 4, label: "下载结果", status: "pending" as const },
    ];
  }

  if (!results.value.length) {
    return [
      { index: 1, label: "批量上传", status: "completed" as const },
      { index: 2, label: "检查上传", status: "current" as const },
      { index: 3, label: "批量导出", status: "pending" as const },
      { index: 4, label: "下载结果", status: "pending" as const },
    ];
  }

  if (resultsOutdated.value) {
    return [
      { index: 1, label: "批量上传", status: "completed" as const },
      { index: 2, label: "检查上传", status: "completed" as const },
      { index: 3, label: "批量导出", status: "current" as const },
      { index: 4, label: "下载结果", status: "pending" as const },
    ];
  }

  return [
    { index: 1, label: "批量上传", status: "completed" as const },
    { index: 2, label: "检查上传", status: "completed" as const },
    { index: 3, label: "批量导出", status: "completed" as const },
    { index: 4, label: "下载结果", status: "current" as const },
  ];
});
const workflowTone = computed(() => {
  if (!selectedFiles.value.length) {
    return "pending";
  }

  if (outputLimitExceeded.value) {
    return "warning";
  }

  if (!results.value.length) {
    return successfulUploads.value.length ? "info" : "warning";
  }

  return resultsOutdated.value ? "warning" : "success";
});
const workflowTitle = computed(() => {
  if (!selectedFiles.value.length) {
    return "先选择一批原图";
  }

  if (outputLimitExceeded.value) {
    return "当前批量输出尺寸过大";
  }

  if (!results.value.length) {
    return successfulUploads.value.length ? "可以开始批量导出了" : "当前没有可处理图片";
  }

  return resultsOutdated.value ? "结果已经落后于当前参数" : "批量结果已经同步";
});
const workflowMessage = computed(() => {
  if (!selectedFiles.value.length) {
    return "上传后会先显示每张图的成功或失败状态，再按统一参数批量导出。";
  }

  if (outputLimitExceeded.value) {
    return outputLimitMessage.value;
  }

  if (!results.value.length) {
    if (!successfulUploads.value.length) {
      return "这批图片里没有通过校验或上传成功的文件，请先处理上传问题。";
    }

    const failedCount = uploadItems.value.length - successfulUploads.value.length;
    return failedCount > 0
      ? `当前可继续处理 ${successfulUploads.value.length} 张成功上传的图片，另有 ${failedCount} 张需要单独检查。`
      : "上传已经完成，确认规格和导出参数后就可以直接开始批量导出。";
  }

  return resultsOutdated.value
    ? "你已经改动了规格、构图或导出参数，请重新批量导出，避免把旧结果一起打包下载。"
    : "下面这些文件已经和当前参数一致，可以逐个查看，也可以直接打包成 ZIP 下载。";
});
const operationSections = computed(() => [
  {
    id: "presets",
    label: "规格",
    summary: `${presets.value.length} 个模板`,
  },
  {
    id: "size",
    label: "尺寸",
    summary: `${size.value.width} x ${size.value.height} ${size.value.unit}`,
  },
  {
    id: "output",
    label: "导出",
    summary: `${output.value.format.toUpperCase()} · ${output.value.dpi} DPI`,
  },
  {
    id: "adjustments",
    label: "调整",
    summary: `${fitMode.value === "fill" ? "填充裁切" : "完整适配"} · 锐化 ${adjustments.value.sharpness}`,
  },
]);

function applyPreset(preset: PresetItem) {
  selectedPresetId.value = preset.id;
  size.value = {
    width: preset.width,
    height: preset.height,
    unit: preset.unit,
    dpi: preset.dpi,
  };
  output.value = {
    ...output.value,
    format: preset.format,
    dpi: preset.dpi,
    target_size_kb_min: preset.target_size_kb_min,
    target_size_kb_max: preset.target_size_kb_max,
    background_color: preset.background_color,
    filename: preset.name,
  };
}

function clearSelection() {
  selectedFiles.value = [];
  uploadItems.value = [];
  results.value = [];
  lastBatchSignature.value = "";
  errorMessage.value = "";
}

function clearResults() {
  results.value = [];
  lastBatchSignature.value = "";
}

async function handleSelectFiles(files: File[]) {
  const validationError = validateBatchImageFiles(files);
  if (validationError) {
    selectedFiles.value = [];
    uploadItems.value = [];
    results.value = [];
    errorMessage.value = validationError;
    return;
  }

  selectedFiles.value = files;
  uploadItems.value = files.map((file, index) => ({
    index,
    name: file.name,
    upload: null,
    error: null,
  }));
  results.value = [];
  lastBatchSignature.value = "";
  errorMessage.value = "";

  uploading.value = true;
  try {
    const response = await uploadImagesBatch(files);
    for (const item of response.items) {
      const target = uploadItems.value[item.index];
      if (!target) {
        continue;
      }
      if (item.ok && item.upload) {
        target.upload = item.upload;
        target.error = null;
      } else {
        target.upload = null;
        target.error = item.error || "上传失败。";
      }
    }
  } catch (error) {
    errorMessage.value = formatApiError(error, "批量上传失败。");
    retryCooldown.startCooldown(getRetryAfterSeconds(error));
  } finally {
    uploading.value = false;
  }
}

async function handleBatchProcess() {
  if (!canProcess.value) {
    return;
  }

  errorMessage.value = "";
  processing.value = true;

  try {
    const uploadSnapshot = [...successfulUploads.value];
    const fileIds = uploadSnapshot.map((item) => item.upload!.file_id);
    const response = await processBatchAuto({
      file_ids: fileIds,
      preset_id: selectedPresetId.value,
      custom_size: size.value,
      viewport_width: viewportWidth.value,
      viewport_height: viewportHeight.value,
      fit_mode: fitMode.value,
      adjustments: adjustments.value,
      output: output.value,
    });
    lastBatchSignature.value = createBatchSignature({
      fileIds,
      presetId: selectedPresetId.value,
      size: size.value,
      viewportWidth: viewportWidth.value,
      viewportHeight: viewportHeight.value,
      fitMode: fitMode.value,
      adjustments: adjustments.value,
      output: output.value,
    });

    results.value = response.items.map((item) => {
      const source = uploadSnapshot[item.index];
      return {
        ...item,
        name: source?.name ?? `#${item.index + 1}`,
        original_index: source?.index ?? item.index,
      };
    });
  } catch (error) {
    errorMessage.value = formatApiError(error, "批量处理失败。");
    retryCooldown.startCooldown(getRetryAfterSeconds(error));
  } finally {
    processing.value = false;
  }
}

async function handleDownloadAll() {
  if (!okTaskIds.value.length) {
    return;
  }

  errorMessage.value = "";
  downloading.value = true;
  try {
    const blob = await downloadZipArchive({
      task_ids: okTaskIds.value,
      filename: output.value.filename || "id-photo-batch",
      include_manifest: true,
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = buildZipDownloadName(output.value.filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (error) {
    errorMessage.value = formatApiError(error, "ZIP 下载失败。");
    retryCooldown.startCooldown(getRetryAfterSeconds(error));
  } finally {
    downloading.value = false;
  }
}

onMounted(async () => {
  try {
    const response = await fetchPresets();
    presets.value = response.items;
    if (!selectedPresetId.value && presets.value.length > 0) {
      applyPreset(presets.value[0]);
    }
  } catch (error) {
    errorMessage.value = formatApiError(error, "规格加载失败。");
  }
});
</script>

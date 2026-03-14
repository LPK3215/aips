<template>
  <main class="app-shell">
    <AppTopNav />

    <section class="hero">
      <div class="hero__copy">
        <p class="eyebrow">AIPS / AI ID Photo Studio</p>
        <h1>上传原图，</h1>
        <h1>直接出片。</h1>
        <p class="hero__lede">
          上传一张原图，选规格、调构图，直接导出可提交文件。
        </p>
      </div>
      <div class="hero__badge">
        <span>真实像素修改</span>
        <span>JPEG 大小逼近</span>
        <span>导出即提交</span>
      </div>
    </section>

    <section class="workspace-grid">
      <div class="workspace-grid__left">
        <FileDropzone
          :preview-url="store.sourceUrl"
          :filename="store.upload?.original_filename ?? ''"
          @select="handleSelectFile"
        />
        <section v-if="store.restoredTaskDraft" class="panel panel--notice">
          <div class="panel__header">
            <div>
              <p class="eyebrow">Restored Draft</p>
              <h3>参数已恢复，等待重新上传原图</h3>
            </div>
            <button class="chip" type="button" @click="store.clearRestoredTaskDraft">隐藏提示</button>
          </div>
          <p class="panel__hint">
            已恢复
            {{ store.restoredTaskDraft.presetName ? `“${store.restoredTaskDraft.presetName}”` : "该任务" }}
            的尺寸、构图、增强和导出参数。为避免误用其他图片，当前上传内容已清空，请重新上传原图后继续编辑。
          </p>
        </section>
        <EditorSectionSwitcher v-model="activeSection" :sections="operationSections" />
        <PresetSelector
          v-show="activeSection === 'presets'"
          :presets="store.presets"
          :selected-id="store.selectedPresetId"
          @select="store.applyPreset"
        />
        <SizeForm v-show="activeSection === 'size'" v-model="store.size" />
        <OutputSettings v-show="activeSection === 'output'" v-model="store.output" />
        <AdjustmentPanel
          v-show="activeSection === 'adjustments'"
          v-model="store.adjustments"
          v-model:fit-mode="fitMode"
        />
        <RecentTasks :items="store.recentTasks" :missing-count="store.recentTasksMissingCount" />
      </div>

      <div class="workspace-grid__right">
        <CropViewport
          ref="cropRef"
          :source-url="store.sourceUrl"
          :natural-width="store.upload?.width_px ?? 0"
          :natural-height="store.upload?.height_px ?? 0"
          :ratio="targetRatio"
          :fit-mode="fitMode"
          :persisted-render="store.restoredTaskDraft ? store.render : null"
          :suggesting="suggesting"
          @change="store.setRender"
          @suggest="handleSuggest"
        />
        <ImageInfoDisclosure
          v-if="store.upload"
          eyebrow="Source Info"
          title="原图信息"
          :summary="sourceInfoSummary"
          hint="默认折叠，点开后可查看文件属性、像素和方向"
          :items="sourceInfoItems"
        />

        <section class="panel">
          <div class="panel__header">
            <div>
              <p class="eyebrow">Processing</p>
              <h3>导出动作</h3>
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
              <strong>当前输出</strong>
              <p>
                {{ resolvedOutputPixels.width }} x {{ resolvedOutputPixels.height }} px ·
                {{ store.output.format.toUpperCase() }} · {{ store.output.dpi }} DPI
              </p>
            </div>
          </div>

          <p v-if="outputLimitExceeded" class="error-text panel__hint panel__hint--compact">{{ outputLimitMessage }}</p>
          <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
          <p v-if="retryCooldown.isCoolingDown.value" class="panel__hint panel__hint--compact">
            限流保护中，{{ retryCooldown.secondsRemaining.value }} 秒后可再次发起处理。
          </p>

          <div class="action-row">
            <button
              class="button button--primary"
              :disabled="!canProcess || processing || retryCooldown.isCoolingDown.value"
              @click="handleProcess"
            >
              {{ processButtonLabel }}
            </button>
          </div>

          <!-- 处理进度条 -->
          <div v-if="processing" class="process-progress">
            <div class="process-progress__bar" :style="{ width: `${processProgress}%` }"></div>
            <div class="process-progress__text">{{ processProgress }}%</div>
          </div>
        </section>

        <section v-if="canProcess || store.lastProcess" ref="resultPreviewRef" class="panel result-preview result-preview--inline">
          <div class="panel__header">
            <div>
              <p class="eyebrow">Preview</p>
              <h3>{{ previewHeading }}</h3>
            </div>
            <span class="status-badge" :class="`status-badge--${previewStatusTone}`">{{ previewStatusLabel }}</span>
          </div>

          <div v-if="!store.lastProcess" class="result-preview__stage result-preview__stage--inline">
            <div class="result-preview__notice">
              <strong>还没有预览结果</strong>
              <p>拖拽构图、调整参数后，点击上方按钮，新生成的结果图会直接显示在这里。</p>
              <small>预览图由后端真实生成，不是浏览器里的临时效果。</small>
            </div>
          </div>

          <template v-else>
            <p v-if="previewOutdated" class="panel__hint panel__hint--compact">
              你已经修改了参数，下方仍是上一次生成的结果。建议先更新预览，再下载或查看结果页。
            </p>
            <p v-else class="panel__hint panel__hint--compact">
              当前预览已经和页面参数同步。可以继续微调，也可以直接下载。
            </p>

            <div class="panel__actions">
              <a
                class="button"
                :class="previewOutdated ? 'button--secondary' : 'button--primary'"
                :href="resultDownloadUrl"
                :download="store.lastProcess.meta.filename"
              >
                {{ previewDownloadLabel }}
              </a>
              <RouterLink
                class="button button--secondary"
                :to="`/result/${store.lastProcess.task_id}`"
              >
                {{ previewResultLinkLabel }}
              </RouterLink>
            </div>
            <div class="result-preview__stage result-preview__stage--inline">
              <img :src="resultPreviewUrl" alt="当前导出预览" class="result-preview__image result-preview__image--inline" />
            </div>
          </template>
        </section>

        <ResultMetaCard v-if="store.lastProcess" :meta="store.lastProcess.meta" :stale="previewOutdated" />
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from "vue";

import {
  buildApiUrl,
  fetchPresets,
  fetchRecentTasks,
  formatApiError,
  getRetryAfterSeconds,
  processImage,
  suggestRender,
  uploadImage,
  waitForTaskCompletion,
} from "../api/client";
import AdjustmentPanel from "../components/AdjustmentPanel.vue";
import AppTopNav from "../components/AppTopNav.vue";
import CropViewport from "../components/CropViewport.vue";
import EditorSectionSwitcher from "../components/EditorSectionSwitcher.vue";
import FileDropzone from "../components/FileDropzone.vue";
import ImageInfoDisclosure from "../components/ImageInfoDisclosure.vue";
import OutputSettings from "../components/OutputSettings.vue";
import PresetSelector from "../components/PresetSelector.vue";
import RecentTasks from "../components/RecentTasks.vue";
import ResultMetaCard from "../components/ResultMetaCard.vue";
import SizeForm from "../components/SizeForm.vue";
import WorkflowSteps from "../components/WorkflowSteps.vue";
import { useRetryCooldown } from "../composables/useRetryCooldown";
import { useEditorStore } from "../stores/editor";
import type { FitMode } from "../types";
import {
  formatAspectRatio,
  formatFileSize,
  formatMegapixels,
  formatOrientation,
  formatPixelSize,
} from "../utils/imageInfo";
import { buildOutputLimitHint, isOutputPixelLimitExceeded, resolveOutputPixels } from "../utils/outputSafety";
import { createWorkbenchSignature } from "../utils/requestSignature";
import { validateImageFile } from "../utils/uploadValidation";


const store = useEditorStore();

const errorMessage = ref("");
const processing = ref(false);
const suggesting = ref(false);
const processProgress = ref(0);
const cropRef = ref<InstanceType<typeof CropViewport> | null>(null);
const resultPreviewRef = ref<HTMLElement | null>(null);
const activeSection = ref("presets");
const retryCooldown = useRetryCooldown();
const fitMode = computed<FitMode>({
  get: () => store.render.fit_mode,
  set: (value) => {
    store.setFitMode(value);
  },
});

const targetRatio = computed(() => {
  if (!store.size.width || !store.size.height) {
    return 413 / 626;
  }

  return store.size.width / store.size.height;
});

const resolvedOutputPixels = computed(() => resolveOutputPixels(store.size));
const outputLimitExceeded = computed(() =>
  isOutputPixelLimitExceeded(resolvedOutputPixels.value.width, resolvedOutputPixels.value.height),
);
const outputLimitMessage = computed(() =>
  buildOutputLimitHint(resolvedOutputPixels.value.width, resolvedOutputPixels.value.height, "当前导出"),
);
const canProcess = computed(() => Boolean(store.upload?.file_id && store.sourceUrl) && !outputLimitExceeded.value);
const sourceInfoSummary = computed(() => {
  if (!store.upload) {
    return "";
  }

  return `${store.upload.width_px} x ${store.upload.height_px} · ${store.upload.format.toUpperCase()} · ${formatFileSize(store.upload.size_bytes)}`;
});
const sourceInfoItems = computed(() => {
  if (!store.upload) {
    return [];
  }

  return [
    {
      label: "文件名",
      value: store.upload.original_filename,
    },
    {
      label: "格式",
      value: store.upload.format.toUpperCase(),
    },
    {
      label: "像素尺寸",
      value: formatPixelSize(store.upload.width_px, store.upload.height_px),
    },
    {
      label: "文件大小",
      value: formatFileSize(store.upload.size_bytes),
    },
    {
      label: "长宽比",
      value: formatAspectRatio(store.upload.width_px, store.upload.height_px),
    },
    {
      label: "图像方向",
      value: formatOrientation(store.upload.width_px, store.upload.height_px),
    },
    {
      label: "像素总量",
      value: formatMegapixels(store.upload.width_px, store.upload.height_px),
    },
  ];
});
const resultPreviewUrl = computed(() => (store.lastProcess ? buildApiUrl(store.lastProcess.result_url) : ""));
const resultDownloadUrl = computed(() => (store.lastProcess ? buildApiUrl(store.lastProcess.download_url) : ""));
const currentProcessSignature = computed(() =>
  createWorkbenchSignature({
    fileId: store.upload?.file_id ?? null,
    presetId: store.selectedPresetId,
    size: store.size,
    render: {
      ...store.render,
      fit_mode: fitMode.value,
    },
    adjustments: store.adjustments,
    output: store.output,
  }),
);
const previewOutdated = computed(
  () =>
    Boolean(
      store.lastProcess &&
      store.lastProcessSignature &&
      currentProcessSignature.value !== store.lastProcessSignature,
    ),
);
const processButtonLabel = computed(() => {
  if (processing.value) {
    return "处理中...";
  }

  if (retryCooldown.isCoolingDown.value) {
    return `${retryCooldown.secondsRemaining.value} 秒后重试`;
  }

  if (previewOutdated.value) {
    return "按当前参数更新预览";
  }

  if (store.lastProcess) {
    return "重新生成预览";
  }

  return "生成预览并导出";
});
const previewHeading = computed(() => {
  if (!store.lastProcess) {
    return "结果预览区";
  }

  return previewOutdated.value ? "上一次导出预览" : "当前导出预览";
});
const previewStatusTone = computed(() => {
  if (!store.lastProcess) {
    return "pending";
  }

  return previewOutdated.value ? "warning" : "success";
});
const previewStatusLabel = computed(() => {
  if (!store.lastProcess) {
    return "未生成";
  }

  return previewOutdated.value ? "待更新" : "已同步";
});
const previewDownloadLabel = computed(() => (previewOutdated.value ? "下载上次图片" : "下载图片"));
const previewResultLinkLabel = computed(() => (previewOutdated.value ? "查看上次结果页" : "查看结果页"));
const workflowSteps = computed(() => {
  if (!store.upload) {
    return [
      { index: 1, label: "上传原图", status: "current" as const },
      { index: 2, label: "调整构图", status: "pending" as const },
      { index: 3, label: "生成预览", status: "pending" as const },
      { index: 4, label: "下载结果", status: "pending" as const },
    ];
  }

  if (!store.lastProcess) {
    return [
      { index: 1, label: "上传原图", status: "completed" as const },
      { index: 2, label: "调整构图", status: "current" as const },
      { index: 3, label: "生成预览", status: "pending" as const },
      { index: 4, label: "下载结果", status: "pending" as const },
    ];
  }

  if (previewOutdated.value) {
    return [
      { index: 1, label: "上传原图", status: "completed" as const },
      { index: 2, label: "调整构图", status: "completed" as const },
      { index: 3, label: "生成预览", status: "current" as const },
      { index: 4, label: "下载结果", status: "pending" as const },
    ];
  }

  return [
    { index: 1, label: "上传原图", status: "completed" as const },
    { index: 2, label: "调整构图", status: "completed" as const },
    { index: 3, label: "生成预览", status: "completed" as const },
    { index: 4, label: "下载结果", status: "current" as const },
  ];
});
const workflowTone = computed(() => {
  if (!store.upload) {
    return "pending";
  }

  if (outputLimitExceeded.value) {
    return "warning";
  }

  if (!store.lastProcess) {
    return "info";
  }

  return previewOutdated.value ? "warning" : "success";
});
const workflowTitle = computed(() => {
  if (!store.upload) {
    return "先上传一张原图";
  }

  if (outputLimitExceeded.value) {
    return "当前导出尺寸过大";
  }

  if (!store.lastProcess) {
    return "可以开始编辑并生成预览";
  }

  return previewOutdated.value ? "下方结果已经落后于当前参数" : "当前结果已经同步";
});
const workflowMessage = computed(() => {
  if (!store.upload) {
    return "上传后左侧可以选规格，右侧可以直接拖拽构图，结果会显示在下方。";
  }

  if (outputLimitExceeded.value) {
    return outputLimitMessage.value;
  }

  if (!store.lastProcess) {
    return "建议先拖拽构图，必要时点“自动居中”，确认输出尺寸后再生成预览。";
  }

  return previewOutdated.value
    ? "你已经改动了构图或导出参数，请重新生成一次，避免把旧结果当成最新结果下载。"
    : "可以继续微调参数再重新生成，也可以直接下载或进入结果页继续后续操作。";
});
const operationSections = computed(() => [
  {
    id: "presets",
    label: "规格",
    summary: `${store.presets.length} 个模板`,
  },
  {
    id: "size",
    label: "尺寸",
    summary: `${store.size.width} x ${store.size.height} ${store.size.unit}`,
  },
  {
    id: "output",
    label: "导出",
    summary: `${store.output.format.toUpperCase()} · ${store.output.dpi} DPI`,
  },
  {
    id: "adjustments",
    label: "调整",
    summary: `${fitMode.value === "fill" ? "填充裁切" : "完整适配"} · 锐化 ${store.adjustments.sharpness}`,
  },
]);

async function loadPresets() {
  const response = await fetchPresets();
  store.setPresets(response.items);
}

async function loadRecentTasks() {
  const response = await fetchRecentTasks(10);
  store.setRecentTasks(response.items, response.missing_count);
}

async function handleSelectFile(file: File, onProgress?: (progress: number) => void) {
  errorMessage.value = "";
  const validationError = validateImageFile(file);
  if (validationError) {
    errorMessage.value = validationError;
    return;
  }

  try {
    const upload = await uploadImage(file, onProgress);
    const sourceUrl = URL.createObjectURL(file);
    store.setUploadedSource({ upload, sourceUrl });
    await loadRecentTasks();
  } catch (error) {
    errorMessage.value = formatApiError(error, "上传失败。");
    retryCooldown.startCooldown(getRetryAfterSeconds(error));
  }
}

async function handleSuggest() {
  if (!store.upload) {
    return;
  }

  errorMessage.value = "";
  suggesting.value = true;
  try {
    const response = await suggestRender({
      file_id: store.upload.file_id,
      custom_size: store.size,
      viewport_width: store.render.viewport_width,
      viewport_height: store.render.viewport_height,
      fit_mode: fitMode.value,
    });
    cropRef.value?.applyRender(response.render);
  } catch (error) {
    errorMessage.value = formatApiError(error, "自动居中失败。");
    retryCooldown.startCooldown(getRetryAfterSeconds(error));
  } finally {
    suggesting.value = false;
  }
}

async function handleProcess() {
  if (!store.upload) {
    return;
  }

  errorMessage.value = "";
  processing.value = true;
  processProgress.value = 0;

  try {
    const payload = {
      file_id: store.upload.file_id,
      preset_id: store.selectedPresetId,
      custom_size: store.size,
      render: {
        ...store.render,
        fit_mode: fitMode.value,
      },
      adjustments: store.adjustments,
      output: store.output,
    };
    const result = await processImage(payload);
    const completedTask = await waitForTaskCompletion(result.task_id, {
      onUpdate: (status) => {
        processProgress.value = status.progress;
      },
    });

    store.lastProcess = {
      task_id: completedTask.task_id,
      result_url: completedTask.result_url,
      download_url: completedTask.download_url,
      meta: completedTask.meta,
    };
    store.lastProcessSignature = createWorkbenchSignature({
      fileId: payload.file_id,
      presetId: payload.preset_id,
      size: payload.custom_size,
      render: payload.render,
      adjustments: payload.adjustments,
      output: payload.output,
    });
    await nextTick();
    resultPreviewRef.value?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
    await loadRecentTasks();
  } catch (error) {
    errorMessage.value = formatApiError(error, "处理失败。");
    retryCooldown.startCooldown(getRetryAfterSeconds(error));
  } finally {
    processing.value = false;
    processProgress.value = 0;
  }
}

onMounted(async () => {
  if (store.lastProcess && !store.lastProcessSignature && currentProcessSignature.value) {
    store.lastProcessSignature = currentProcessSignature.value;
  }

  try {
    await Promise.all([loadPresets(), loadRecentTasks()]);
  } catch (error) {
    errorMessage.value = formatApiError(error, "规格加载失败。");
  }
});
</script>

<style scoped>
.process-progress {
  margin: 16px 0;
  height: 8px;
  background-color: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.process-progress__bar {
  height: 100%;
  background-color: #3b82f6;
  transition: width 0.3s ease;
}

.process-progress__text {
  position: absolute;
  top: 12px;
  right: 0;
  font-size: 12px;
  color: #666;
}
</style>

<template>
  <main class="app-shell">
    <AppTopNav />

    <section class="hero hero--compact">
      <div class="hero__copy">
        <p class="eyebrow">RESIZE TOOL</p>
        <h1>改尺寸，直接导出。</h1>
        <p class="hero__lede">
          上传一张图，按像素改宽高，当前页直接查看结果。
        </p>
      </div>
      <div class="hero__badge">
        <span>锁定比例</span>
        <span>快速倍数</span>
        <RouterLink class="button button--secondary" to="/tools">返回工具中心</RouterLink>
      </div>
    </section>

    <section class="workspace-grid">
      <div class="workspace-grid__left">
        <FileDropzone
          :preview-url="sourceUrl"
          :filename="upload?.original_filename ?? ''"
          @select="handleSelectFile"
        />

        <ImageInfoDisclosure
          v-if="upload"
          eyebrow="Source Info"
          title="原图信息"
          :summary="sourceInfoSummary"
          hint="默认折叠，点开后查看像素、比例和文件大小"
          :items="sourceInfoItems"
        />

        <section class="panel">
          <div class="panel__header">
            <div>
              <p class="eyebrow">Resize</p>
              <h3>尺寸设置</h3>
            </div>
            <div class="panel__actions">
              <button class="chip" type="button" :disabled="!upload" @click="syncToOriginalSize">恢复原尺寸</button>
            </div>
          </div>

          <div class="chip-row chip-row--dense">
            <button
              v-for="item in scalePresets"
              :key="item.value"
              class="chip"
              type="button"
              :disabled="!upload"
              @click="applyScale(item.value)"
            >
              {{ item.label }}
            </button>
          </div>

          <div class="form-grid">
            <label class="field">
              <span>宽度 px</span>
              <input
                :value="resize.width_px || ''"
                type="number"
                min="1"
                step="1"
                :disabled="!upload"
                @input="handleWidthInput"
              />
            </label>
            <label class="field">
              <span>高度 px</span>
              <input
                :value="resize.height_px || ''"
                type="number"
                min="1"
                step="1"
                :disabled="!upload"
                @input="handleHeightInput"
              />
            </label>
            <label class="field field--inline toggle field--full">
              <span>锁定原图比例</span>
              <input v-model="keepAspect" type="checkbox" :disabled="!upload" />
            </label>
          </div>

          <p class="panel__hint">
            {{ resizeHint }}
          </p>
        </section>

        <ToolOutputSettings v-model="output" />
      </div>

      <div class="workspace-grid__right">
        <section class="panel">
          <div class="panel__header">
            <div>
              <p class="eyebrow">Run</p>
              <h3>缩放导出</h3>
            </div>
          </div>

          <div class="status-stack">
            <div class="status-card">
              <strong>原图尺寸</strong>
              <p v-if="upload">{{ upload.width_px }} x {{ upload.height_px }} px</p>
              <p v-else>先上传图片。</p>
            </div>
            <div class="status-card">
              <strong>当前目标</strong>
              <p>{{ resize.width_px || 0 }} x {{ resize.height_px || 0 }} px · {{ formatMegapixelCount(resize.width_px || 0, resize.height_px || 0) }}</p>
            </div>
          </div>

          <p v-if="resizeLimitExceeded" class="error-text panel__hint panel__hint--compact">{{ resizeLimitMessage }}</p>
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
        </section>

        <section v-if="canProcess || result" ref="resultPreviewRef" class="panel result-preview result-preview--inline">
          <div class="panel__header">
            <div>
              <p class="eyebrow">Preview</p>
              <h3>{{ previewHeading }}</h3>
            </div>
            <span class="status-badge" :class="`status-badge--${previewStatusTone}`">{{ previewStatusLabel }}</span>
          </div>

          <div v-if="!result" class="result-preview__stage result-preview__stage--inline">
            <div class="result-preview__notice">
              <strong>还没有结果</strong>
              <p>设置好目标宽高后点击导出，缩放后的图片会直接显示在这里。</p>
              <small>这是后端真实生成的新文件，不是浏览器拉伸预览。</small>
            </div>
          </div>

          <template v-else>
            <p v-if="previewOutdated" class="panel__hint panel__hint--compact">
              你已经修改了目标尺寸或导出参数，下方仍是上一次生成的结果。
            </p>
            <p v-else class="panel__hint panel__hint--compact">
              当前结果和页面参数一致，可以继续微调后再生成，或直接下载。
            </p>

            <div class="panel__actions">
              <a
                class="button"
                :class="previewOutdated ? 'button--secondary' : 'button--primary'"
                :href="resultDownloadUrl"
                :download="result.meta.filename"
              >
                {{ previewOutdated ? "下载上次图片" : "下载图片" }}
              </a>
              <RouterLink class="button button--secondary" :to="`/result/${result.task_id}`">
                {{ previewOutdated ? "查看上次结果页" : "查看结果页" }}
              </RouterLink>
            </div>

            <div class="result-preview__stage result-preview__stage--inline">
              <img :src="resultPreviewUrl" alt="缩放结果预览" class="result-preview__image result-preview__image--inline result-preview__image--wide" />
            </div>
          </template>
        </section>

        <ResultMetaCard v-if="result" :meta="result.meta" :stale="previewOutdated" />
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref } from "vue";

import {
  buildApiUrl,
  formatApiError,
  getRetryAfterSeconds,
  resizeImageTool,
  uploadImage,
  waitForTaskCompletion,
} from "../api/client";
import AppTopNav from "../components/AppTopNav.vue";
import FileDropzone from "../components/FileDropzone.vue";
import ImageInfoDisclosure from "../components/ImageInfoDisclosure.vue";
import ResultMetaCard from "../components/ResultMetaCard.vue";
import ToolOutputSettings from "../components/ToolOutputSettings.vue";
import { useRetryCooldown } from "../composables/useRetryCooldown";
import type { BasicOutputState, ProcessResponse, ResizeToolState, UploadResponse } from "../types";
import {
  formatAspectRatio,
  formatFileSize,
  formatMegapixels,
  formatOrientation,
  formatPixelSize,
} from "../utils/imageInfo";
import { buildOutputLimitHint, formatMegapixelCount, isOutputPixelLimitExceeded } from "../utils/outputSafety";
import { createResizeSignature } from "../utils/requestSignature";
import { validateImageFile } from "../utils/uploadValidation";


const upload = ref<UploadResponse | null>(null);
const sourceUrl = ref("");
const resize = ref<ResizeToolState>({
  width_px: 0,
  height_px: 0,
});
const keepAspect = ref(true);
const output = ref<BasicOutputState>({
  format: "jpg",
  dpi: 300,
  quality: 90,
  filename: "resized-image",
  background_color: "#ffffff",
});
const processing = ref(false);
const errorMessage = ref("");
const result = ref<ProcessResponse | null>(null);
const lastSignature = ref("");
const resultPreviewRef = ref<HTMLElement | null>(null);
const retryCooldown = useRetryCooldown();

const scalePresets = [
  { label: "50%", value: 0.5 },
  { label: "75%", value: 0.75 },
  { label: "150%", value: 1.5 },
  { label: "200%", value: 2 },
];

const sourceRatio = computed(() => {
  if (!upload.value?.width_px || !upload.value?.height_px) {
    return 1;
  }
  return upload.value.width_px / upload.value.height_px;
});
const resizeLimitExceeded = computed(() =>
  isOutputPixelLimitExceeded(resize.value.width_px, resize.value.height_px),
);
const resizeLimitMessage = computed(() =>
  buildOutputLimitHint(resize.value.width_px, resize.value.height_px, "当前目标"),
);
const canProcess = computed(
  () => Boolean(upload.value?.file_id && resize.value.width_px && resize.value.height_px) && !resizeLimitExceeded.value,
);
const sourceInfoSummary = computed(() => {
  if (!upload.value) {
    return "";
  }
  return `${upload.value.width_px} x ${upload.value.height_px} · ${upload.value.format.toUpperCase()} · ${formatFileSize(upload.value.size_bytes)}`;
});
const sourceInfoItems = computed(() => {
  if (!upload.value) {
    return [];
  }

  return [
    { label: "文件名", value: upload.value.original_filename },
    { label: "格式", value: upload.value.format.toUpperCase() },
    { label: "像素尺寸", value: formatPixelSize(upload.value.width_px, upload.value.height_px) },
    { label: "文件大小", value: formatFileSize(upload.value.size_bytes) },
    { label: "长宽比", value: formatAspectRatio(upload.value.width_px, upload.value.height_px) },
    { label: "图像方向", value: formatOrientation(upload.value.width_px, upload.value.height_px) },
    { label: "像素总量", value: formatMegapixels(upload.value.width_px, upload.value.height_px) },
  ];
});
const currentSignature = computed(() =>
  createResizeSignature({
    fileId: upload.value?.file_id ?? null,
    resize: resize.value,
    output: output.value,
  }),
);
const previewOutdated = computed(() => Boolean(result.value && lastSignature.value && currentSignature.value !== lastSignature.value));
const processButtonLabel = computed(() => {
  if (processing.value) {
    return "处理中...";
  }
  if (retryCooldown.isCoolingDown.value) {
    return `${retryCooldown.secondsRemaining.value} 秒后重试`;
  }
  if (previewOutdated.value) {
    return "按当前尺寸更新结果";
  }
  return result.value ? "重新导出缩放结果" : "生成缩放结果";
});
const previewHeading = computed(() => {
  if (!result.value) {
    return "结果预览区";
  }
  return previewOutdated.value ? "上一次缩放结果" : "当前缩放结果";
});
const previewStatusTone = computed(() => {
  if (!result.value) {
    return "pending";
  }
  return previewOutdated.value ? "warning" : "success";
});
const previewStatusLabel = computed(() => {
  if (!result.value) {
    return "未生成";
  }
  return previewOutdated.value ? "待更新" : "已同步";
});
const resultPreviewUrl = computed(() => (result.value ? buildApiUrl(result.value.result_url) : ""));
const resultDownloadUrl = computed(() => (result.value ? buildApiUrl(result.value.download_url) : ""));
const resizeHint = computed(() => {
  if (!upload.value) {
    return "上传后会自动带入原图像素尺寸。";
  }
  if (resizeLimitExceeded.value) {
    return resizeLimitMessage.value;
  }
  if (!keepAspect.value) {
    return `当前允许自由改宽高，目标约 ${formatMegapixelCount(resize.value.width_px, resize.value.height_px)}。`;
  }
  return `当前锁定原图比例 ${formatAspectRatio(upload.value.width_px, upload.value.height_px)}，改一边会自动推算另一边。目标约 ${formatMegapixelCount(resize.value.width_px, resize.value.height_px)}。`;
});

function fileStem(filename: string) {
  return filename.replace(/\.[^/.]+$/, "");
}

function revokeSourceUrl() {
  if (sourceUrl.value.startsWith("blob:")) {
    URL.revokeObjectURL(sourceUrl.value);
  }
}

function syncToOriginalSize() {
  if (!upload.value) {
    return;
  }
  resize.value = {
    width_px: upload.value.width_px,
    height_px: upload.value.height_px,
  };
}

function applyScale(multiplier: number) {
  if (!upload.value) {
    return;
  }
  resize.value = {
    width_px: Math.max(1, Math.round(upload.value.width_px * multiplier)),
    height_px: Math.max(1, Math.round(upload.value.height_px * multiplier)),
  };
}

function handleWidthInput(event: Event) {
  const input = event.target as HTMLInputElement;
  const nextWidth = Math.max(1, Math.round(Number(input.value) || 0));
  resize.value.width_px = nextWidth;

  if (keepAspect.value && upload.value) {
    resize.value.height_px = Math.max(1, Math.round(nextWidth / sourceRatio.value));
  }
}

function handleHeightInput(event: Event) {
  const input = event.target as HTMLInputElement;
  const nextHeight = Math.max(1, Math.round(Number(input.value) || 0));
  resize.value.height_px = nextHeight;

  if (keepAspect.value && upload.value) {
    resize.value.width_px = Math.max(1, Math.round(nextHeight * sourceRatio.value));
  }
}

async function handleSelectFile(file: File) {
  errorMessage.value = "";
  const validationError = validateImageFile(file);
  if (validationError) {
    errorMessage.value = validationError;
    return;
  }

  try {
    const uploaded = await uploadImage(file);
    revokeSourceUrl();
    upload.value = uploaded;
    sourceUrl.value = URL.createObjectURL(file);
    resize.value = {
      width_px: uploaded.width_px,
      height_px: uploaded.height_px,
    };
    output.value = {
      ...output.value,
      filename: `${fileStem(file.name)}-resized`,
    };
    result.value = null;
    lastSignature.value = "";
  } catch (error) {
    errorMessage.value = formatApiError(error, "上传失败。");
    retryCooldown.startCooldown(getRetryAfterSeconds(error));
  }
}

async function handleProcess() {
  if (!upload.value) {
    return;
  }

  errorMessage.value = "";
  processing.value = true;

  try {
    const submittedTask = await resizeImageTool({
      file_id: upload.value.file_id,
      width_px: resize.value.width_px,
      height_px: resize.value.height_px,
      output: output.value,
    });
    const completedTask = await waitForTaskCompletion(submittedTask.task_id);
    result.value = {
      task_id: completedTask.task_id,
      result_url: completedTask.result_url,
      download_url: completedTask.download_url,
      meta: completedTask.meta,
    };
    lastSignature.value = currentSignature.value;
    await nextTick();
    resultPreviewRef.value?.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    errorMessage.value = formatApiError(error, "缩放失败。");
    retryCooldown.startCooldown(getRetryAfterSeconds(error));
  } finally {
    processing.value = false;
  }
}

onBeforeUnmount(() => {
  revokeSourceUrl();
});
</script>

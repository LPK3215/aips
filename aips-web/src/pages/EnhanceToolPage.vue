<template>
  <main class="app-shell">
    <AppTopNav />

    <section class="hero hero--compact">
      <div class="hero__copy">
        <p class="eyebrow">ENHANCE TOOL</p>
        <h1>轻度增强，直接预览。</h1>
        <p class="hero__lede">
          上传一张图，做放大、去噪、锐化和对比度增强。
        </p>
      </div>
      <div class="hero__badge">
        <span>轻度增强</span>
        <span>可选放大</span>
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
              <p class="eyebrow">Enhance</p>
              <h3>增强参数</h3>
            </div>
            <div class="panel__actions">
              <button class="chip" type="button" @click="resetEnhance">恢复默认</button>
            </div>
          </div>

          <label class="field field--inline">
            <span>放大倍率</span>
            <AppSelect v-model="scaleFactorValue" :options="scaleFactorOptions" />
          </label>

          <div class="slider-stack">
            <label v-for="item in sliderItems" :key="item.key" class="slider">
              <div class="slider__row">
                <span>{{ item.label }}</span>
                <strong>{{ enhance[item.key] }}</strong>
              </div>
              <input
                v-model.number="enhance[item.key]"
                :min="item.min"
                :max="item.max"
                :step="item.step"
                type="range"
              />
            </label>
          </div>

          <label class="field field--inline toggle">
            <span>自动拉伸层次</span>
            <input v-model="enhance.auto_contrast" type="checkbox" />
          </label>

          <p class="panel__hint">
            {{ enhanceHint }}
          </p>
        </section>

        <ToolOutputSettings v-model="output" />
      </div>

      <div class="workspace-grid__right">
        <section class="panel">
          <div class="panel__header">
            <div>
              <p class="eyebrow">Run</p>
              <h3>增强导出</h3>
            </div>
          </div>

          <div class="status-stack">
            <div class="status-card">
              <strong>原图尺寸</strong>
              <p v-if="upload">{{ upload.width_px }} x {{ upload.height_px }} px</p>
              <p v-else>先上传图片。</p>
            </div>
            <div class="status-card">
              <strong>预计输出</strong>
              <p>{{ estimatedSizeText }}</p>
            </div>
          </div>

          <p class="panel__hint panel__hint--compact">
            当前更适合常规增强，不适合承诺“重度去马赛克”或“严重失焦修复”。
          </p>
          <p v-if="enhanceLimitExceeded" class="error-text panel__hint panel__hint--compact">{{ enhanceLimitMessage }}</p>
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
              <p>设置好增强参数后点击导出，增强后的图片会直接显示在这里。</p>
              <small>增强结果以当前算法输出为准，不是浏览器前端模拟效果。</small>
            </div>
          </div>

          <template v-else>
            <p v-if="previewOutdated" class="panel__hint panel__hint--compact">
              你已经修改了增强参数，下方仍是上一次生成的结果。
            </p>
            <p v-else class="panel__hint panel__hint--compact">
              当前结果和页面参数一致，可以直接下载，也可以继续微调后再生成。
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
              <img :src="resultPreviewUrl" alt="增强结果预览" class="result-preview__image result-preview__image--inline result-preview__image--wide" />
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
  enhanceImageTool,
  formatApiError,
  getRetryAfterSeconds,
  uploadImage,
  waitForTaskCompletion,
} from "../api/client";
import AppTopNav from "../components/AppTopNav.vue";
import AppSelect from "../components/AppSelect.vue";
import FileDropzone from "../components/FileDropzone.vue";
import ImageInfoDisclosure from "../components/ImageInfoDisclosure.vue";
import ResultMetaCard from "../components/ResultMetaCard.vue";
import ToolOutputSettings from "../components/ToolOutputSettings.vue";
import { useRetryCooldown } from "../composables/useRetryCooldown";
import type { BasicOutputState, EnhanceToolState, ProcessResponse, UploadResponse } from "../types";
import {
  formatAspectRatio,
  formatFileSize,
  formatMegapixels,
  formatOrientation,
  formatPixelSize,
} from "../utils/imageInfo";
import { buildOutputLimitHint, formatMegapixelCount, isOutputPixelLimitExceeded } from "../utils/outputSafety";
import { createEnhanceSignature } from "../utils/requestSignature";
import { validateImageFile } from "../utils/uploadValidation";


const DEFAULT_ENHANCE: EnhanceToolState = {
  scale_factor: 1.5,
  denoise: 8,
  sharpness: 32,
  contrast: 10,
  auto_contrast: true,
};

const upload = ref<UploadResponse | null>(null);
const sourceUrl = ref("");
const enhance = ref<EnhanceToolState>({ ...DEFAULT_ENHANCE });
const output = ref<BasicOutputState>({
  format: "jpg",
  dpi: 300,
  quality: 90,
  filename: "enhanced-image",
  background_color: "#ffffff",
});
const processing = ref(false);
const errorMessage = ref("");
const result = ref<ProcessResponse | null>(null);
const lastSignature = ref("");
const resultPreviewRef = ref<HTMLElement | null>(null);
const retryCooldown = useRetryCooldown();

const scaleFactorOptions = [
  { value: "1", label: "1.0x", description: "不放大，只做增强" },
  { value: "1.5", label: "1.5x", description: "常用的轻度放大" },
  { value: "2", label: "2.0x", description: "适合较小图再放大" },
  { value: "3", label: "3.0x", description: "放大更明显，但更吃原图质量" },
] as const;

const sliderItems = [
  { key: "denoise", label: "去噪", min: 0, max: 30, step: 1 },
  { key: "sharpness", label: "锐化", min: 0, max: 100, step: 1 },
  { key: "contrast", label: "对比度", min: -30, max: 50, step: 1 },
] as const;

const scaleFactorValue = computed({
  get: () => enhance.value.scale_factor.toString(),
  set: (value: string) => {
    enhance.value.scale_factor = Number(value);
  },
});
const estimatedWidthPx = computed(() =>
  upload.value ? Math.round(upload.value.width_px * enhance.value.scale_factor) : 0,
);
const estimatedHeightPx = computed(() =>
  upload.value ? Math.round(upload.value.height_px * enhance.value.scale_factor) : 0,
);
const enhanceLimitExceeded = computed(() =>
  isOutputPixelLimitExceeded(estimatedWidthPx.value, estimatedHeightPx.value),
);
const enhanceLimitMessage = computed(() =>
  buildOutputLimitHint(estimatedWidthPx.value, estimatedHeightPx.value, "增强后的输出"),
);
const canProcess = computed(() => Boolean(upload.value?.file_id) && !enhanceLimitExceeded.value);
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
const estimatedSizeText = computed(() => {
  if (!upload.value) {
    return "等待上传";
  }
  return `${estimatedWidthPx.value} x ${estimatedHeightPx.value} px · ${formatMegapixelCount(estimatedWidthPx.value, estimatedHeightPx.value)}`;
});
const currentSignature = computed(() =>
  createEnhanceSignature({
    fileId: upload.value?.file_id ?? null,
    enhance: enhance.value,
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
    return "按当前参数更新结果";
  }
  return result.value ? "重新生成增强结果" : "生成增强结果";
});
const previewHeading = computed(() => {
  if (!result.value) {
    return "结果预览区";
  }
  return previewOutdated.value ? "上一次增强结果" : "当前增强结果";
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
const enhanceHint = computed(() => {
  if (!upload.value) {
    return "上传后可以直接调放大、去噪、锐化和对比度。";
  }
  if (enhanceLimitExceeded.value) {
    return enhanceLimitMessage.value;
  }
  return `预计输出 ${estimatedSizeText.value}。当前更适合轻度增强，不建议把参数一次拉到极限。`;
});

function fileStem(filename: string) {
  return filename.replace(/\.[^/.]+$/, "");
}

function revokeSourceUrl() {
  if (sourceUrl.value.startsWith("blob:")) {
    URL.revokeObjectURL(sourceUrl.value);
  }
}

function resetEnhance() {
  enhance.value = { ...DEFAULT_ENHANCE };
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
    output.value = {
      ...output.value,
      filename: `${fileStem(file.name)}-enhanced`,
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
    const submittedTask = await enhanceImageTool({
      file_id: upload.value.file_id,
      scale_factor: enhance.value.scale_factor,
      denoise: enhance.value.denoise,
      sharpness: enhance.value.sharpness,
      contrast: enhance.value.contrast,
      auto_contrast: enhance.value.auto_contrast,
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
    errorMessage.value = formatApiError(error, "增强失败。");
    retryCooldown.startCooldown(getRetryAfterSeconds(error));
  } finally {
    processing.value = false;
  }
}

onBeforeUnmount(() => {
  revokeSourceUrl();
});
</script>

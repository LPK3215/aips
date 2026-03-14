<template>
  <main class="app-shell app-shell--result">
    <AppTopNav />

    <section class="hero hero--compact">
      <div class="hero__copy">
        <p class="eyebrow">RESULT SHEET</p>
        <h1>结果已生成，可直接下载。</h1>
        <p class="hero__lede">这里显示的是后端真实生成的结果文件，可直接下载或继续排版。</p>
      </div>
      <div class="hero__badge">
        <span>真实导出文件</span>
        <span>支持继续排版</span>
        <RouterLink class="button button--secondary" to="/">返回工作台</RouterLink>
      </div>
    </section>

    <section v-if="loading" class="panel">
      <p>正在读取结果...</p>
    </section>

    <section v-else-if="errorMessage" class="panel">
      <p class="error-text">{{ errorMessage }}</p>
    </section>

    <section v-else-if="task" class="result-layout">
      <div class="panel result-preview">
        <div class="panel__header">
          <div>
            <p class="eyebrow">Preview</p>
            <h3>{{ task.file_available ? "导出图" : "结果文件已过期" }}</h3>
          </div>
        </div>
        <div class="result-preview__stage">
          <img v-if="task.file_available" :src="imageUrl" alt="处理结果" class="result-preview__image" />
          <div v-else class="result-preview__notice">
            <strong>文件已被自动清理</strong>
            <p>任务参数仍然保留，但导出图片已经超过保留期，无法继续预览、下载或打印排版。</p>
            <small>如果你还保留原始照片，可以回到工作台按相同参数重新处理。</small>
          </div>
        </div>
        <div class="action-row">
          <a
            v-if="task.file_available"
            class="button button--primary"
            :href="downloadUrl"
            :download="task.meta.filename"
          >
            下载图片
          </a>
          <button
            v-if="canRestoreToWorkbench"
            class="button button--secondary"
            type="button"
            @click="handleRestoreToWorkbench"
          >
            按当前参数回到工作台
          </button>
          <RouterLink class="button button--secondary" to="/">继续处理下一张</RouterLink>
        </div>
        <p v-if="restoreError" class="error-text result-preview__error">{{ restoreError }}</p>
      </div>

      <div class="result-layout__side">
        <ResultMetaCard :meta="task.meta" />

        <section v-if="task.file_available" class="panel">
          <div class="panel__header">
            <div>
              <p class="eyebrow">Print</p>
              <h3>打印排版</h3>
            </div>
          </div>

          <div class="form-grid">
            <label class="field field--full">
              <span>纸张</span>
              <AppSelect v-model="sheetPreset" :options="sheetPresetOptions" />
            </label>
            <label class="field field--inline toggle field--full">
              <span>自动铺满</span>
              <input v-model="autoGrid" type="checkbox" />
            </label>
            <label class="field">
              <span>列数</span>
              <input v-model.number="sheetCols" min="1" max="20" type="number" :disabled="autoGrid" />
            </label>
            <label class="field">
              <span>行数</span>
              <input v-model.number="sheetRows" min="1" max="20" type="number" :disabled="autoGrid" />
            </label>
            <label class="field field--inline toggle field--full">
              <span>切割角标</span>
              <input v-model="showCutLines" type="checkbox" />
            </label>
          </div>

          <p v-if="sheetError" class="error-text">{{ sheetError }}</p>
          <p v-if="retryCooldown.isCoolingDown.value" class="panel__hint panel__hint--compact">
            限流保护中，{{ retryCooldown.secondsRemaining.value }} 秒后可再次生成排版图。
          </p>

          <div class="action-row">
            <button
              class="button button--primary"
              type="button"
              :disabled="sheetLoading || retryCooldown.isCoolingDown.value"
              @click="handleComposeSheet"
            >
              {{
                sheetLoading
                  ? "生成中..."
                  : retryCooldown.isCoolingDown.value
                    ? `${retryCooldown.secondsRemaining.value} 秒后重试`
                    : "生成排版图"
              }}
            </button>
          </div>

          <p class="panel__hint">
            排版会基于当前导出图重复铺满纸张，并在后端真实生成新文件。建议用于打印/冲印。
          </p>
        </section>

        <section v-else class="panel">
          <div class="panel__header">
            <div>
              <p class="eyebrow">Status</p>
              <h3>恢复路径</h3>
            </div>
          </div>

          <p class="panel__hint">
            当前仅保留任务元信息和参数快照。若需重新生成，请返回工作台重新上传原图，或复制下方 JSON 作为参考参数。
          </p>
        </section>

        <section v-if="task.params" class="panel">
          <div class="panel__header">
            <div>
              <p class="eyebrow">Params</p>
              <h3>处理参数</h3>
            </div>
            <button class="chip" type="button" @click="copyParams">复制 JSON</button>
          </div>

          <details>
            <summary>展开查看</summary>
            <pre class="code-block">{{ paramsText }}</pre>
          </details>

          <p class="panel__hint">
            这份 JSON 是后端保存的真实处理参数，可用于复现或排查问题。
          </p>
        </section>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import {
  buildApiUrl,
  composeSheet,
  fetchTask,
  formatApiError,
  getRetryAfterSeconds,
  waitForTaskCompletion,
} from "../api/client";
import AppTopNav from "../components/AppTopNav.vue";
import AppSelect from "../components/AppSelect.vue";
import ResultMetaCard from "../components/ResultMetaCard.vue";
import { useRetryCooldown } from "../composables/useRetryCooldown";
import { useEditorStore } from "../stores/editor";
import type { TaskDetailResponse } from "../types";


const route = useRoute();
const router = useRouter();
const store = useEditorStore();
const loading = ref(true);
const errorMessage = ref("");
const task = ref<TaskDetailResponse | null>(null);
const restoreError = ref("");

const imageUrl = computed(() => (task.value ? buildApiUrl(task.value.result_url) : ""));
const downloadUrl = computed(() => (task.value ? buildApiUrl(task.value.download_url) : ""));
const paramsText = computed(() => (task.value?.params ? JSON.stringify(task.value.params, null, 2) : ""));
const canRestoreToWorkbench = computed(() => {
  const params = task.value?.params;
  if (!params || typeof params !== "object") {
    return false;
  }

  return (
    "file_id" in params &&
    "custom_size" in params &&
    "render" in params &&
    "adjustments" in params &&
    "output" in params
  );
});

const sheetPreset = ref<"a4-300" | "4x6-300">("a4-300");
const sheetPresetOptions = [
  { value: "a4-300", label: "A4 · 300 DPI", description: "标准 A4 打印排版" },
  { value: "4x6-300", label: "6 寸 (4x6\") · 300 DPI", description: "常见冲印尺寸" },
] as const;
const autoGrid = ref(true);
const sheetCols = ref(2);
const sheetRows = ref(3);
const showCutLines = ref(true);
const sheetLoading = ref(false);
const sheetError = ref("");
let loadToken = 0;
const retryCooldown = useRetryCooldown();

function resolvePageSize() {
  if (sheetPreset.value === "4x6-300") {
    return { width: 4, height: 6, unit: "inch" as const, dpi: 300 };
  }
  return { width: 210, height: 297, unit: "mm" as const, dpi: 300 };
}

async function handleComposeSheet() {
  if (!task.value?.file_available) {
    return;
  }

  sheetError.value = "";
  sheetLoading.value = true;
  try {
    const baseName = task.value.meta.filename.replace(/\.[^/.]+$/, "");
    const response = await composeSheet({
      task_id: task.value.task_id,
      page_size: resolvePageSize(),
      margin_mm: 6,
      gap_mm: 4,
      cols: autoGrid.value ? null : sheetCols.value,
      rows: autoGrid.value ? null : sheetRows.value,
      copies: null,
      show_cut_lines: showCutLines.value,
      cut_line_color: "#1b1b1b",
      cut_line_width: 2,
      output: {
        format: "jpg",
        dpi: 300,
        quality: 92,
        filename: `${baseName}-print`,
        background_color: "#ffffff",
      },
    });

    await waitForTaskCompletion(response.task_id);
    await router.push(`/result/${response.task_id}`);
  } catch (error) {
    sheetError.value = formatApiError(error, "生成排版失败。");
    retryCooldown.startCooldown(getRetryAfterSeconds(error));
  } finally {
    sheetLoading.value = false;
  }
}

async function copyParams() {
  if (!paramsText.value) {
    return;
  }

  try {
    await navigator.clipboard.writeText(paramsText.value);
  } catch {
    // Fallback for older browsers.
    const textarea = document.createElement("textarea");
    textarea.value = paramsText.value;
    textarea.setAttribute("readonly", "true");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    textarea.remove();
  }
}

async function handleRestoreToWorkbench() {
  restoreError.value = "";
  if (!task.value?.params) {
    restoreError.value = "当前任务没有可恢复的参数快照。";
    return;
  }

  const restored = store.restoreFromTaskParams(
    task.value.task_id,
    task.value.params,
    task.value.meta.preset_name ?? null,
  );
  if (!restored) {
    restoreError.value = "当前任务参数快照不完整，无法回填到工作台。";
    return;
  }

  await router.push("/");
}

async function loadTask(taskId: string) {
  const currentToken = ++loadToken;
  task.value = null;
  errorMessage.value = "";
  restoreError.value = "";
  loading.value = true;

  if (!taskId) {
    errorMessage.value = "缺少任务编号。";
    loading.value = false;
    return;
  }

  try {
    const response = await fetchTask(taskId);
    if (currentToken !== loadToken) {
      return;
    }
    task.value = response;
  } catch (error) {
    if (currentToken !== loadToken) {
      return;
    }
    errorMessage.value = formatApiError(error, "读取处理结果失败。");
  } finally {
    if (currentToken === loadToken) {
      loading.value = false;
    }
  }
}

watch(
  () => String(route.params.taskId || ""),
  (taskId) => {
    void loadTask(taskId);
  },
  { immediate: true },
);
</script>

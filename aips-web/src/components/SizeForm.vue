<template>
  <section class="panel">
    <div class="panel__header">
      <div>
        <p class="eyebrow">Size</p>
        <h3>尺寸与单位</h3>
      </div>
    </div>

    <div class="form-grid">
      <label class="field">
        <span>宽度</span>
        <input v-model.number="model.width" min="1" step="0.1" type="number" />
      </label>
      <label class="field">
        <span>高度</span>
        <input v-model.number="model.height" min="1" step="0.1" type="number" />
      </label>
      <label class="field">
        <span>单位</span>
        <AppSelect v-model="model.unit" :options="unitOptions" />
      </label>
      <label class="field">
        <span>DPI</span>
        <input v-model.number="model.dpi" min="72" max="600" step="1" type="number" />
      </label>

      <div class="size-summary field--full">
        <strong>实际导出像素</strong>
        <p>{{ resolvedPixels.width }} x {{ resolvedPixels.height }} px</p>
        <small>
          {{ model.unit === "px" ? "当前直接按像素输出。" : `已按 ${model.dpi} DPI 自动换算，后端会按这个像素尺寸真实生成文件。` }}
        </small>
        <small v-if="outputLimitExceeded" class="error-text">{{ outputLimitMessage }}</small>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import AppSelect from "./AppSelect.vue";
import type { SizeFormState } from "../types";
import { buildOutputLimitHint, isOutputPixelLimitExceeded, resolveOutputPixels } from "../utils/outputSafety";


const model = defineModel<SizeFormState>({ required: true });
const unitOptions = [
  { value: "px", label: "像素 px", description: "直接按像素输出" },
  { value: "mm", label: "毫米 mm", description: "适合证件物理尺寸" },
  { value: "cm", label: "厘米 cm", description: "最常用的证件照单位" },
  { value: "inch", label: "英寸 inch", description: "适合海外规格和打印" },
] as const;

const resolvedPixels = computed(() => resolveOutputPixels(model.value));
const outputLimitExceeded = computed(() =>
  isOutputPixelLimitExceeded(resolvedPixels.value.width, resolvedPixels.value.height),
);
const outputLimitMessage = computed(() =>
  buildOutputLimitHint(resolvedPixels.value.width, resolvedPixels.value.height, "当前尺寸"),
);
</script>

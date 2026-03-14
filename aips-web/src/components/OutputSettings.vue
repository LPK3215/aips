<template>
  <section class="panel output-settings">
    <div class="panel__header">
      <div>
        <p class="eyebrow">Output</p>
        <h3>导出参数</h3>
      </div>
    </div>

    <div class="form-grid">
      <label class="field">
        <span>格式</span>
        <AppSelect v-model="model.format" :options="formatOptions" />
      </label>
      <label class="field">
        <span>DPI</span>
        <input v-model.number="model.dpi" min="72" max="600" type="number" />
      </label>
      <label class="field">
        <span>JPG 质量</span>
        <input v-model.number="model.quality" min="35" max="100" type="number" :disabled="model.format === 'png'" />
      </label>
      <label class="field">
        <span>背景</span>
        <input v-model="model.background_color" type="color" />
      </label>
      <label class="field field--full">
        <span>常用底色</span>
        <div class="chip-row">
          <button
            v-for="preset in colorPresets"
            :key="preset.value"
            type="button"
            class="chip chip--swatch"
            :class="{ 'chip--active': model.background_color.toLowerCase() === preset.value }"
            @click="model.background_color = preset.value"
          >
            <span class="chip__swatch" :style="{ '--swatch': preset.value }" aria-hidden="true" />
            {{ preset.label }}
          </button>
        </div>
      </label>
      <label class="field field--toggle">
        <span>自动抠图换底</span>
        <input v-model="model.replace_background" type="checkbox" />
      </label>
      <label class="field">
        <span>最小体积 KB</span>
        <input v-model.number="minValue" min="1" type="number" :disabled="model.format === 'png'" />
      </label>
      <label class="field">
        <span>最大体积 KB</span>
        <input v-model.number="maxValue" min="1" type="number" :disabled="model.format === 'png'" />
      </label>
      <label v-if="model.replace_background" class="field field--full">
        <span>边缘柔和</span>
        <input v-model.number="model.replace_feather" min="0" max="24" step="1" type="range" />
      </label>
      <label class="field field--full">
        <span>文件名</span>
        <input v-model="model.filename" type="text" placeholder="id-photo-result" />
      </label>
    </div>

    <p class="panel__hint">
      PNG 可保透明；需要控制体积时用 JPG。
    </p>
    <p class="panel__hint" v-if="model.replace_background">
      自动抠图后会换成纯色底。背景复杂时，边缘可能不够干净。
    </p>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import AppSelect from "./AppSelect.vue";
import type { OutputState } from "../types";


const model = defineModel<OutputState>({ required: true });
const formatOptions = [
  { value: "jpg", label: "JPG", description: "体积小，便于提交" },
  { value: "png", label: "PNG", description: "保透明，文件更大" },
] as const;

const colorPresets = [
  { label: "白", value: "#ffffff" },
  { label: "蓝", value: "#2f67d1" },
  { label: "红", value: "#d22630" },
] as const;

const minValue = computed({
  get: () => model.value.target_size_kb_min ?? undefined,
  set: (value: number | undefined) => {
    model.value.target_size_kb_min = Number.isFinite(value) ? Number(value) : null;
  },
});

const maxValue = computed({
  get: () => model.value.target_size_kb_max ?? undefined,
  set: (value: number | undefined) => {
    model.value.target_size_kb_max = Number.isFinite(value) ? Number(value) : null;
  },
});
</script>

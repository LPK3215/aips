<template>
  <section class="panel">
    <div class="panel__header">
      <div>
        <p class="eyebrow">Output</p>
        <h3>导出设置</h3>
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
        <span>背景色</span>
        <input v-model="model.background_color" type="color" />
      </label>
      <label class="field field--full">
        <span>文件名</span>
        <input v-model="model.filename" type="text" placeholder="tool-result" />
      </label>
    </div>

    <p class="panel__hint">
      PNG 更适合保留透明边缘；JPG 体积更小，适合直接下载和分享。
    </p>
  </section>
</template>

<script setup lang="ts">
import type { BasicOutputState } from "../types";
import AppSelect from "./AppSelect.vue";


const model = defineModel<BasicOutputState>({ required: true });

const formatOptions = [
  { value: "jpg", label: "JPG", description: "通用体积更小" },
  { value: "png", label: "PNG", description: "边缘更稳，适合透明源图" },
] as const;
</script>

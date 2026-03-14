<template>
  <section class="panel">
    <div class="panel__header">
      <div>
        <p class="eyebrow">Adjustments</p>
        <h3>画质与构图</h3>
      </div>
      <div class="panel__actions">
        <button class="chip" type="button" @click="resetAdjustments">恢复默认</button>
      </div>
    </div>

    <label class="field field--inline">
      <span>构图模式</span>
      <AppSelect v-model="fitMode" :options="fitModeOptions" />
    </label>

    <div class="slider-stack">
      <label v-for="item in sliderConfig" :key="item.key" class="slider">
        <div class="slider__row">
          <span>{{ item.label }}</span>
          <strong>{{ model[item.key] }}</strong>
        </div>
        <input
          v-model.number="model[item.key]"
          :min="item.min"
          :max="item.max"
          :step="item.step"
          type="range"
        />
      </label>
    </div>
  </section>
</template>

<script setup lang="ts">
import AppSelect from "./AppSelect.vue";
import type { AdjustmentState, FitMode } from "../types";


const DEFAULT_ADJUSTMENTS: AdjustmentState = {
  brightness: 0,
  contrast: 0,
  saturation: 0,
  sharpness: 18,
  blur: 0,
};

const model = defineModel<AdjustmentState>({ required: true });
const fitMode = defineModel<FitMode>("fitMode", { required: true });
const fitModeOptions = [
  { value: "fill", label: "填充裁切", description: "画面铺满规格区域" },
  { value: "fit", label: "完整适配", description: "完整保留原图内容" },
] as const;

const sliderConfig = [
  { key: "brightness", label: "亮度", min: -100, max: 100, step: 1 },
  { key: "contrast", label: "对比度", min: -100, max: 100, step: 1 },
  { key: "saturation", label: "饱和度", min: -100, max: 100, step: 1 },
  { key: "sharpness", label: "锐化", min: 0, max: 100, step: 1 },
  { key: "blur", label: "模糊", min: 0, max: 20, step: 1 },
] as const;

function resetAdjustments() {
  model.value = { ...DEFAULT_ADJUSTMENTS };
  fitMode.value = "fill";
}
</script>

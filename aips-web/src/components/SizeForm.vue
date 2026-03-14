<template>
  <section class="panel">
    <div class="panel__header">
      <div>
        <p class="eyebrow">Size</p>
        <h3>尺寸与单位</h3>
      </div>
    </div>
    <p class="panel__hint panel__hint--compact">
      先选单位，再填宽高。切换单位时会自动换算成当前单位的数值。
    </p>

    <div class="form-grid">
      <label class="field">
        <span>单位</span>
        <AppSelect v-model="unitModel" :options="unitOptions" />
      </label>
      <label class="field">
        <span>{{ dpiLabel }}</span>
        <input v-model.number="model.dpi" min="72" max="600" step="1" type="number" :disabled="isPixelUnit" />
      </label>
      <label class="field">
        <span>{{ widthLabel }}</span>
        <input v-model.number="model.width" :min="inputMin" :step="inputStep" type="number" />
      </label>
      <label class="field">
        <span>{{ heightLabel }}</span>
        <input v-model.number="model.height" :min="inputMin" :step="inputStep" type="number" />
      </label>

      <div class="size-summary field--full">
        <strong>{{ sizeSummaryTitle }}</strong>
        <p>{{ formattedInputSize }}</p>
        <small>{{ sizeSummaryHint }}</small>
        <small v-if="outputLimitExceeded" class="error-text">{{ outputLimitMessage }}</small>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";

import AppSelect from "./AppSelect.vue";
import type { SizeFormState, SizeUnit } from "../types";
import { buildOutputLimitHint, isOutputPixelLimitExceeded, resolveOutputPixels } from "../utils/outputSafety";


const model = defineModel<SizeFormState>({ required: true });
const unitOptions = [
  { value: "px", label: "像素 px", description: "直接按像素输出" },
  { value: "mm", label: "毫米 mm", description: "适合证件物理尺寸" },
  { value: "cm", label: "厘米 cm", description: "常用的证件照单位" },
  { value: "inch", label: "英寸 inch", description: "适合海外规格" },
] as const;

const resolvedPixels = computed(() => resolveOutputPixels(model.value));
const outputLimitExceeded = computed(() =>
  isOutputPixelLimitExceeded(resolvedPixels.value.width, resolvedPixels.value.height),
);
const outputLimitMessage = computed(() =>
  buildOutputLimitHint(resolvedPixels.value.width, resolvedPixels.value.height, "当前尺寸"),
);
const isPixelUnit = computed(() => model.value.unit === "px");
const widthLabel = computed(() => `宽度（${model.value.unit}）`);
const heightLabel = computed(() => `高度（${model.value.unit}）`);
const dpiLabel = computed(() => (isPixelUnit.value ? "换算 DPI（当前不参与）" : "换算 DPI"));
const inputMin = computed(() => (isPixelUnit.value ? 1 : 0.1));
const inputStep = computed(() => (isPixelUnit.value ? 1 : 0.1));
const formattedInputSize = computed(
  () => `${formatForUnit(model.value.width, model.value.unit)} x ${formatForUnit(model.value.height, model.value.unit)} ${model.value.unit}`,
);
const sizeSummaryTitle = computed(() => (isPixelUnit.value ? "当前按像素输入" : "当前按物理尺寸输入"));
const sizeSummaryHint = computed(() =>
  isPixelUnit.value
    ? "当前直接按像素输出。上方 DPI 不参与尺寸换算。"
    : `按 ${model.value.dpi} DPI 换算，实际导出约 ${resolvedPixels.value.width} x ${resolvedPixels.value.height} px。`,
);

const unitModel = computed({
  get: () => model.value.unit,
  set: (nextUnit: string) => {
    if (!isSizeUnit(nextUnit) || nextUnit === model.value.unit) {
      return;
    }

    const dpi = normalizeDpi(model.value.dpi);
    model.value.width = convertValue(model.value.width, model.value.unit, nextUnit, dpi);
    model.value.height = convertValue(model.value.height, model.value.unit, nextUnit, dpi);
    model.value.unit = nextUnit;
  },
});

function isSizeUnit(value: string): value is SizeUnit {
  return value === "px" || value === "mm" || value === "cm" || value === "inch";
}

function normalizeDpi(value: number) {
  return Number.isFinite(value) && value >= 72 ? value : 300;
}

function toInches(value: number, unit: SizeUnit, dpi: number) {
  const safeValue = Number.isFinite(value) && value > 0 ? value : unit === "px" ? 1 : 0.1;

  if (unit === "px") {
    return safeValue / dpi;
  }

  if (unit === "mm") {
    return safeValue / 25.4;
  }

  if (unit === "cm") {
    return safeValue / 2.54;
  }

  return safeValue;
}

function fromInches(valueInInches: number, unit: SizeUnit, dpi: number) {
  if (unit === "px") {
    return Math.max(1, Math.round(valueInInches * dpi));
  }

  const rawValue =
    unit === "mm"
      ? valueInInches * 25.4
      : unit === "cm"
        ? valueInInches * 2.54
        : valueInInches;

  return roundForUnit(Math.max(0.1, rawValue), unit);
}

function convertValue(value: number, fromUnit: SizeUnit, toUnit: SizeUnit, dpi: number) {
  return fromInches(toInches(value, fromUnit, dpi), toUnit, dpi);
}

function roundForUnit(value: number, unit: SizeUnit) {
  const digits = unit === "mm" ? 1 : 2;
  return Number(value.toFixed(digits));
}

function formatForUnit(value: number, unit: SizeUnit) {
  if (unit === "px") {
    return `${Math.max(1, Math.round(Number(value) || 0))}`;
  }

  return `${roundForUnit(Number(value) || 0.1, unit)}`;
}
</script>

<template>
  <ImageInfoDisclosure
    :eyebrow="eyebrow"
    :title="resolvedTitle"
    :summary="summary"
    :hint="resolvedHint"
    :status-label="resolvedStatusLabel"
    :status-tone="resolvedStatusTone"
    :items="items"
  />
</template>

<script setup lang="ts">
import { computed } from "vue";

import type { ResultMeta } from "../types";
import {
  formatAspectRatio,
  formatKilobytes,
  formatMegapixels,
  formatOrientation,
  formatPixelSize,
} from "../utils/imageInfo";
import ImageInfoDisclosure from "./ImageInfoDisclosure.vue";


const props = withDefaults(
  defineProps<{
    meta: ResultMeta;
    eyebrow?: string;
    title?: string;
    hint?: string;
    stale?: boolean;
  }>(),
  {
    eyebrow: "Result Info",
    title: "导出图信息",
    hint: "点击展开查看像素、DPI、文件大小等信息",
    stale: false,
  },
);

const resolvedTitle = computed(() => (props.stale ? `上一次${props.title}` : props.title));
const resolvedHint = computed(() =>
  props.stale ? "当前页面参数已变化，这里显示的是上一次导出文件的信息。" : props.hint,
);
const resolvedStatusLabel = computed(() => (props.stale ? "旧结果" : ""));
const resolvedStatusTone = computed(() => (props.stale ? "warning" : "pending"));
const summary = computed(
  () =>
    `${props.meta.width_px} x ${props.meta.height_px} · ${props.meta.format.toUpperCase()} · ${formatKilobytes(props.meta.size_kb)}`,
);

const items = computed(() => [
  {
    label: "文件名",
    value: props.meta.filename,
  },
  {
    label: "格式",
    value: props.meta.format.toUpperCase(),
  },
  {
    label: "像素尺寸",
    value: formatPixelSize(props.meta.width_px, props.meta.height_px),
  },
  {
    label: "文件大小",
    value: formatKilobytes(props.meta.size_kb),
  },
  {
    label: "DPI",
    value: `${props.meta.dpi}`,
  },
  {
    label: "长宽比",
    value: formatAspectRatio(props.meta.width_px, props.meta.height_px),
  },
  {
    label: "图像方向",
    value: formatOrientation(props.meta.width_px, props.meta.height_px),
  },
  {
    label: "像素总量",
    value: formatMegapixels(props.meta.width_px, props.meta.height_px),
  },
  {
    label: "背景色",
    value: props.meta.background_color,
  },
  {
    label: "规格",
    value: props.meta.preset_name || "自定义",
  },
]);
</script>

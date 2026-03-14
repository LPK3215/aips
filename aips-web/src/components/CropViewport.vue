<template>
  <section class="panel panel--viewport">
    <div class="panel__header">
      <div>
        <p class="eyebrow">Viewport</p>
        <h3>拖拽与缩放构图</h3>
      </div>
      <div class="panel__actions">
        <button class="chip" type="button" :disabled="!sourceUrl || suggesting" @click="$emit('suggest')">
          {{ suggesting ? "分析中..." : "自动居中" }}
        </button>
        <button class="chip" type="button" :disabled="!sourceUrl" @click="handleReset">重置</button>
        <small>{{ Math.round(zoom * 100) }}%</small>
      </div>
    </div>

    <div class="viewport-shell">
      <div
        ref="viewportRef"
        class="viewport"
        :style="{
          width: `${viewport.width}px`,
          height: `${viewport.height}px`,
        }"
        @pointerdown="startDrag"
        @wheel.prevent="onWheel"
      >
        <div v-if="!sourceUrl" class="viewport__empty">
          <p>上传图片后，在这里拖拽构图。</p>
          <small>滚轮或下方滑块用于缩放。</small>
        </div>
        <img
          v-if="sourceUrl"
          class="viewport__image"
          :src="sourceUrl"
          alt="待裁剪图片"
          :style="imageStyle"
          draggable="false"
        />
        <div class="viewport__guides">
          <span class="viewport__guide viewport__guide--vertical"></span>
          <span class="viewport__guide viewport__guide--horizontal"></span>
        </div>
        <div class="viewport__frame"></div>
      </div>
    </div>

    <div class="slider-stack slider-stack--compact">
      <label class="slider">
        <div class="slider__row">
          <span>缩放</span>
          <strong>{{ zoom.toFixed(2) }}x</strong>
        </div>
        <input v-model.number="zoom" min="1" max="3.5" step="0.01" type="range" />
      </label>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";

import type { FitMode, RenderState } from "../types";


const props = defineProps<{
  sourceUrl: string;
  naturalWidth: number;
  naturalHeight: number;
  ratio: number;
  fitMode: FitMode;
  persistedRender?: RenderState | null;
  suggesting?: boolean;
}>();

const emit = defineEmits<{
  change: [render: RenderState];
  suggest: [];
}>();

const viewportRef = ref<HTMLElement | null>(null);
const zoom = ref(1);
const offsetX = ref(0);
const offsetY = ref(0);
const hydratedPersistedRender = ref(false);
const hydratedSourceUrl = ref("");

const dragging = ref(false);
const dragPointerId = ref<number | null>(null);
const startX = ref(0);
const startY = ref(0);
const startOffsetX = ref(0);
const startOffsetY = ref(0);

const viewport = computed(() => {
  const maxWidth = 420;
  const maxHeight = 540;
  const ratio = props.ratio > 0 ? props.ratio : 0.66;
  const boundedRatio = maxWidth / maxHeight;

  if (ratio >= boundedRatio) {
    return { width: maxWidth, height: maxWidth / ratio };
  }

  return { width: maxHeight * ratio, height: maxHeight };
});

const baseScale = computed(() => {
  if (!props.naturalWidth || !props.naturalHeight) {
    return 1;
  }

  const widthScale = viewport.value.width / props.naturalWidth;
  const heightScale = viewport.value.height / props.naturalHeight;

  return props.fitMode === "fill"
    ? Math.max(widthScale, heightScale)
    : Math.min(widthScale, heightScale);
});

const effectiveScale = computed(() => baseScale.value * zoom.value);

const displayWidth = computed(() => props.naturalWidth * effectiveScale.value);
const displayHeight = computed(() => props.naturalHeight * effectiveScale.value);

const imageStyle = computed(() => {
  const left = viewport.value.width / 2 + offsetX.value;
  const top = viewport.value.height / 2 + offsetY.value;

  return {
    width: `${displayWidth.value}px`,
    height: `${displayHeight.value}px`,
    left: `${left}px`,
    top: `${top}px`,
    transform: "translate(-50%, -50%)",
  };
});

function clampOffsets(nextX: number, nextY: number) {
  const width = displayWidth.value;
  const height = displayHeight.value;

  const maxX =
    props.fitMode === "fill"
      ? Math.max(0, (width - viewport.value.width) / 2)
      : Math.max(0, (width + viewport.value.width) / 2);

  const maxY =
    props.fitMode === "fill"
      ? Math.max(0, (height - viewport.value.height) / 2)
      : Math.max(0, (height + viewport.value.height) / 2);

  offsetX.value = Math.min(maxX, Math.max(-maxX, nextX));
  offsetY.value = Math.min(maxY, Math.max(-maxY, nextY));
}

function emitState() {
  emit("change", {
    viewport_width: Number(viewport.value.width.toFixed(2)),
    viewport_height: Number(viewport.value.height.toFixed(2)),
    scale: Number(effectiveScale.value.toFixed(6)),
    offset_x: Number(offsetX.value.toFixed(2)),
    offset_y: Number(offsetY.value.toFixed(2)),
    fit_mode: props.fitMode,
  });
}

function resetTransform(shouldEmit = true) {
  zoom.value = 1;
  offsetX.value = 0;
  offsetY.value = 0;
  if (shouldEmit) {
    emitState();
  }
}

function handleReset() {
  resetTransform();
}

function startDrag(event: PointerEvent) {
  if (!props.sourceUrl) {
    return;
  }

  dragging.value = true;
  dragPointerId.value = event.pointerId;
  startX.value = event.clientX;
  startY.value = event.clientY;
  startOffsetX.value = offsetX.value;
  startOffsetY.value = offsetY.value;
  viewportRef.value?.setPointerCapture(event.pointerId);
}

function onPointerMove(event: PointerEvent) {
  if (!dragging.value || event.pointerId !== dragPointerId.value) {
    return;
  }

  const deltaX = event.clientX - startX.value;
  const deltaY = event.clientY - startY.value;
  clampOffsets(startOffsetX.value + deltaX, startOffsetY.value + deltaY);
  emitState();
}

function endDrag(event: PointerEvent) {
  if (event.pointerId !== dragPointerId.value) {
    return;
  }

  dragging.value = false;
  dragPointerId.value = null;
  viewportRef.value?.releasePointerCapture(event.pointerId);
}

function onWheel(event: WheelEvent) {
  const delta = event.deltaY > 0 ? -0.08 : 0.08;
  zoom.value = Math.min(3.5, Math.max(1, Number((zoom.value + delta).toFixed(2))));
}

watch(
  () => [props.sourceUrl, props.naturalWidth, props.naturalHeight, props.fitMode, props.ratio],
  () => {
    if (props.sourceUrl !== hydratedSourceUrl.value) {
      hydratedPersistedRender.value = false;
      hydratedSourceUrl.value = props.sourceUrl;
    }

    if (!props.sourceUrl || !props.naturalWidth || !props.naturalHeight) {
      resetTransform(false);
      return;
    }

    if (!hydratedPersistedRender.value && props.persistedRender) {
      hydratedPersistedRender.value = true;
      applyRender(props.persistedRender);
      return;
    }

    resetTransform();
  },
  { immediate: true },
);

watch([zoom, displayWidth, displayHeight], () => {
  clampOffsets(offsetX.value, offsetY.value);
  emitState();
});

watch(viewportRef, (element, previous) => {
  previous?.removeEventListener("pointermove", onPointerMove);
  previous?.removeEventListener("pointerup", endDrag);
  previous?.removeEventListener("pointercancel", endDrag);

  if (element) {
    element.addEventListener("pointermove", onPointerMove);
    element.addEventListener("pointerup", endDrag);
    element.addEventListener("pointercancel", endDrag);
  }
});

onBeforeUnmount(() => {
  viewportRef.value?.removeEventListener("pointermove", onPointerMove);
  viewportRef.value?.removeEventListener("pointerup", endDrag);
  viewportRef.value?.removeEventListener("pointercancel", endDrag);
});

function applyRender(render: RenderState) {
  if (!props.naturalWidth || !props.naturalHeight) {
    return;
  }

  const nextZoom = render.scale / baseScale.value;
  zoom.value = Math.min(3.5, Math.max(1, Number(nextZoom.toFixed(3))));
  offsetX.value = render.offset_x;
  offsetY.value = render.offset_y;
  clampOffsets(offsetX.value, offsetY.value);
  emitState();
}

defineExpose({ applyRender });
</script>

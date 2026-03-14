<template>
  <section class="panel">
    <div
      class="dropzone"
      :class="{ 'dropzone--active': isDragging }"
      @dragenter.prevent="isDragging = true"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
    >
      <div class="dropzone__copy">
        <p class="eyebrow">Source</p>
        <h3>上传一张原始证件照</h3>
        <p>支持 JPG / PNG，单张不超过 10MB。建议上传清晰原图，系统会在后端真实生成新文件。</p>
      </div>
      <label class="button button--primary">
        选择图片
        <input class="visually-hidden" type="file" accept="image/png,image/jpeg" @change="onFileInput" />
      </label>
    </div>

    <div v-if="previewUrl" class="upload-preview">
      <img class="upload-preview__image" :src="previewUrl" alt="上传预览" />
      <div class="upload-preview__meta">
        <p>{{ filename }}</p>
        <small>本地预览，处理参数以后端导出结果为准。</small>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";


const emit = defineEmits<{
  select: [file: File];
}>();

defineProps<{
  previewUrl: string;
  filename: string;
}>();

const isDragging = ref(false);

function emitFile(file: File | null) {
  if (!file) {
    return;
  }
  emit("select", file);
}

function onDrop(event: DragEvent) {
  isDragging.value = false;
  emitFile(event.dataTransfer?.files?.[0] ?? null);
}

function onFileInput(event: Event) {
  const input = event.target as HTMLInputElement;
  emitFile(input.files?.[0] ?? null);
  input.value = "";
}
</script>

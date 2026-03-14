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
        <p class="eyebrow">Batch</p>
        <h3>批量上传原图</h3>
        <p>支持 JPG / PNG，单张不超过 10MB，单次最多 20 张。多张图片会按相同规格与参数自动居中后批量导出。</p>
      </div>
      <label class="button button--primary">
        选择多张图片
        <input
          class="visually-hidden"
          type="file"
          multiple
          accept="image/png,image/jpeg"
          @change="onFileInput"
        />
      </label>
    </div>

    <div v-if="files.length" class="batch-preview">
      <div class="batch-preview__header">
        <strong>已选择 {{ files.length }} 张</strong>
        <button type="button" class="button button--secondary" @click="emit('clear')">清空</button>
      </div>
      <div class="batch-preview__list">
        <div v-for="file in files" :key="file.name + file.size + file.lastModified" class="batch-preview__item">
          <span class="batch-preview__dot" aria-hidden="true" />
          <div class="batch-preview__meta">
            <p>{{ file.name }}</p>
            <small>{{ Math.round(file.size / 1024) }} KB</small>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";


defineProps<{
  files: File[];
}>();

const emit = defineEmits<{
  select: [files: File[]];
  clear: [];
}>();

const isDragging = ref(false);

function emitFiles(fileList: FileList | null | undefined) {
  if (!fileList || fileList.length === 0) {
    return;
  }
  const files = Array.from(fileList).filter((file) => file.type.startsWith("image/"));
  if (files.length === 0) {
    return;
  }
  emit("select", files);
}

function onDrop(event: DragEvent) {
  isDragging.value = false;
  emitFiles(event.dataTransfer?.files);
}

function onFileInput(event: Event) {
  const input = event.target as HTMLInputElement;
  emitFiles(input.files);
  input.value = "";
}
</script>

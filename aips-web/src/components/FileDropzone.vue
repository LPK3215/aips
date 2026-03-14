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
      <label class="button button--primary" :disabled="uploading || processing">
        {{ processing ? '处理中...' : uploading ? '上传中...' : '选择图片' }}
        <input class="visually-hidden" type="file" accept="image/png,image/jpeg" @change="onFileInput" :disabled="uploading || processing" />
      </label>
    </div>

    <!-- 上传进度条 -->
    <div v-if="uploading" class="upload-progress">
      <div class="upload-progress__bar" :style="{ width: `${uploadProgress}%` }"></div>
      <div class="upload-progress__text">{{ uploadProgress }}%</div>
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
import { workerManager } from "../workers/worker-manager";


const emit = defineEmits<{
  select: [file: File, onProgress: (progress: number) => void];
}>();

defineProps<{
  previewUrl: string;
  filename: string;
}>();

const isDragging = ref(false);
const uploading = ref(false);
const uploadProgress = ref(0);
const processing = ref(false);

async function processImageWithWorker(file: File): Promise<File> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const img = new Image();
        img.onload = async () => {
          // 创建Canvas并绘制图像
          const canvas = document.createElement('canvas');
          canvas.width = img.width;
          canvas.height = img.height;
          const ctx = canvas.getContext('2d');
          
          if (!ctx) {
            reject(new Error('无法创建Canvas上下文'));
            return;
          }
          
          ctx.drawImage(img, 0, 0);
          const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
          
          // 使用Worker处理图像
          processing.value = true;
          const result = await workerManager.processImage(imageData, {
            maxWidth: 1920,
            maxHeight: 1080,
            quality: 0.8
          });
          
          // 将处理后的图像转换回File对象
          const base64 = result.result.split(',')[1];
          const blob = new Blob([Uint8Array.from(atob(base64), c => c.charCodeAt(0))], { type: 'image/jpeg' });
          const processedFile = new File([blob], file.name, { type: 'image/jpeg' });
          
          processing.value = false;
          resolve(processedFile);
        };
        img.onerror = () => {
          reject(new Error('图像加载失败'));
        };
        img.src = e.target?.result as string;
      } catch (error) {
        processing.value = false;
        reject(error);
      }
    };
    reader.onerror = () => {
      reject(new Error('文件读取失败'));
    };
    reader.readAsDataURL(file);
  });
}

async function emitFile(file: File | null) {
  if (!file) {
    return;
  }
  
  uploading.value = true;
  uploadProgress.value = 0;
  
  try {
    // 使用Worker预处理图像
    const processedFile = await processImageWithWorker(file);
    
    const onProgress = (progress: number) => {
      uploadProgress.value = progress;
      if (progress >= 100) {
        uploading.value = false;
      }
    };
    
    emit("select", processedFile, onProgress);
  } catch (error) {
    console.error('图像处理失败:', error);
    // 如果Worker处理失败，使用原始文件
    const onProgress = (progress: number) => {
      uploadProgress.value = progress;
      if (progress >= 100) {
        uploading.value = false;
      }
    };
    emit("select", file, onProgress);
  }
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

<style scoped>
.upload-progress {
  margin: 16px 0;
  height: 8px;
  background-color: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.upload-progress__bar {
  height: 100%;
  background-color: #3b82f6;
  transition: width 0.3s ease;
}

.upload-progress__text {
  position: absolute;
  top: 12px;
  right: 0;
  font-size: 12px;
  color: #666;
}
</style>

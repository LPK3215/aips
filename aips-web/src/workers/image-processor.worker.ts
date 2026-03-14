// 图像预处理Worker

interface ProcessImageMessage {
  type: 'processImage';
  id: string;
  imageData: ImageData;
  options: {
    maxWidth?: number;
    maxHeight?: number;
    quality?: number;
  };
}

interface ProcessImageResponse {
  type: 'processImage';
  id: string;
  result: string; // Base64 encoded image
  width: number;
  height: number;
}

interface ErrorMessage {
  type: 'error';
  id: string;
  message: string;
}

type WorkerMessage = ProcessImageMessage | ErrorMessage;

self.addEventListener('message', (event: MessageEvent<WorkerMessage>) => {
  const message = event.data;

  if (message.type === 'processImage') {
    processImage(message);
  }
});

async function processImage(message: ProcessImageMessage) {
  try {
    // 创建Canvas元素进行图像处理
    const canvas = new OffscreenCanvas(message.imageData.width, message.imageData.height);
    const ctx = canvas.getContext('2d');

    if (!ctx) {
      throw new Error('无法创建Canvas上下文');
    }

    // 绘制原始图像
    ctx.putImageData(message.imageData, 0, 0);

    // 调整图像大小
    const { maxWidth = 1920, maxHeight = 1080, quality = 0.8 } = message.options;
    let newWidth = message.imageData.width;
    let newHeight = message.imageData.height;

    // 计算新尺寸
    if (newWidth > maxWidth || newHeight > maxHeight) {
      const widthRatio = maxWidth / newWidth;
      const heightRatio = maxHeight / newHeight;
      const ratio = Math.min(widthRatio, heightRatio);
      newWidth = Math.floor(newWidth * ratio);
      newHeight = Math.floor(newHeight * ratio);
    }

    // 创建调整大小后的Canvas
    const resizedCanvas = new OffscreenCanvas(newWidth, newHeight);
    const resizedCtx = resizedCanvas.getContext('2d');

    if (!resizedCtx) {
      throw new Error('无法创建调整大小后的Canvas上下文');
    }

    // 绘制调整大小后的图像
    resizedCtx.drawImage(canvas, 0, 0, newWidth, newHeight);

    // 将Canvas转换为Base64编码的图像
    const result = await resizedCanvas.convertToBlob({
      type: 'image/jpeg',
      quality: quality
    });

    // 读取Blob为Base64
    const reader = new FileReader();
    reader.readAsDataURL(result);

    reader.onloadend = () => {
      const base64data = reader.result as string;

      const response: ProcessImageResponse = {
        type: 'processImage',
        id: message.id,
        result: base64data,
        width: newWidth,
        height: newHeight
      };

      self.postMessage(response);
    };
  } catch (error) {
    const errorMessage: ErrorMessage = {
      type: 'error',
      id: message.id,
      message: error instanceof Error ? error.message : '图像处理失败'
    };
    self.postMessage(errorMessage);
  }
}

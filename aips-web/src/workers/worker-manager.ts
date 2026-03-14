// Worker管理器

// 由于 image-processor.worker.ts 不是模块，无法直接导入类型
// 此处手动声明所需类型以保持类型安全
type ProcessImageMessage = {
  type: 'processImage';
  id: string;
  imageData: ImageData;
  options: {
    maxWidth?: number;
    maxHeight?: number;
    quality?: number;
  };
};

type ProcessImageResponse = {
  type: 'processImage';
  id: string;
  result: string;
  width: number;
  height: number;
};

type ErrorMessage = {
  type: 'error';
  id: string;
  message: string;
};

type WorkerCallback = (result: ProcessImageResponse | ErrorMessage) => void;

class WorkerManager {
  private worker: Worker | null = null;
  private callbacks: Map<string, WorkerCallback> = new Map();
  private messageId = 0;

  constructor() {
    this.initializeWorker();
  }

  private initializeWorker() {
    try {
      this.worker = new Worker(new URL('./image-processor.worker.ts', import.meta.url), {
        type: 'module'
      });

      this.worker.addEventListener('message', (event: MessageEvent<ProcessImageResponse | ErrorMessage>) => {
        const response = event.data;
        const callback = this.callbacks.get(response.id);
        if (callback) {
          callback(response);
          this.callbacks.delete(response.id);
        }
      });

      this.worker.addEventListener('error', (error) => {
        console.error('Worker error:', error);
      });
    } catch (error) {
      console.error('Failed to initialize worker:', error);
    }
  }

  processImage(imageData: ImageData, options: {
    maxWidth?: number;
    maxHeight?: number;
    quality?: number;
  }): Promise<ProcessImageResponse> {
    return new Promise((resolve, reject) => {
      if (!this.worker) {
        reject(new Error('Worker not initialized'));
        return;
      }

      const id = this.messageId++;
      const message: ProcessImageMessage = {
        type: 'processImage',
        id: id.toString(),
        imageData,
        options
      };

      this.callbacks.set(id.toString(), (response) => {
        if ('result' in response) {
          resolve(response);
        } else {
          reject(new Error(response.message));
        }
      });

      this.worker.postMessage(message);
    });
  }

  terminate() {
    if (this.worker) {
      this.worker.terminate();
      this.worker = null;
    }
    this.callbacks.clear();
  }
}

// 导出单例实例
export const workerManager = new WorkerManager();

import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

type RuntimeSettings = {
  backend?: {
    host?: string;
    port?: number;
  };
  frontend?: {
    host?: string;
    port?: number;
  };
};

function loadRuntimeSettings(): Required<RuntimeSettings> {
  const currentDir = dirname(fileURLToPath(import.meta.url));
  const configPath = resolve(currentDir, "..", "aips.settings.json");
  const defaults: Required<RuntimeSettings> = {
    backend: {
      host: "127.0.0.1",
      port: 8000,
    },
    frontend: {
      host: "127.0.0.1",
      port: 5173,
    },
  };

  try {
    const parsed = JSON.parse(readFileSync(configPath, "utf-8")) as RuntimeSettings;
    return {
      backend: {
        host: parsed.backend?.host ?? defaults.backend.host,
        port: parsed.backend?.port ?? defaults.backend.port,
      },
      frontend: {
        host: parsed.frontend?.host ?? defaults.frontend.host,
        port: parsed.frontend?.port ?? defaults.frontend.port,
      },
    };
  } catch {
    return defaults;
  }
}

const runtimeSettings = loadRuntimeSettings();
const backendTarget = `http://${runtimeSettings.backend.host}:${runtimeSettings.backend.port}`;

export default defineConfig({
  plugins: [vue()],
  server: {
    host: runtimeSettings.frontend.host,
    port: runtimeSettings.frontend.port,
    proxy: {
      "/api": {
        target: backendTarget,
        changeOrigin: true,
      },
    },
  },
});

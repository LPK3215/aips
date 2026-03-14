import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

function readString(value: string | undefined, fallback: string): string {
  const normalized = value?.trim();
  return normalized ? normalized : fallback;
}

function readPort(value: string | undefined, fallback: number): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function readBoolean(value: string | undefined, fallback: boolean): boolean {
  const normalized = value?.trim().toLowerCase();
  if (!normalized) {
    return fallback;
  }

  return ["1", "true", "yes", "on"].includes(normalized);
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const appHost = readString(env.VITE_APP_HOST, "127.0.0.1");
  const appPort = readPort(env.VITE_APP_PORT, 5173);
  const apiProxyTarget = readString(
    env.VITE_API_PROXY_TARGET,
    env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
  );
  const openBrowser = readBoolean(env.VITE_DEV_OPEN_BROWSER, true);

  return {
    plugins: [vue()],
    server: {
      host: appHost,
      port: appPort,
      open: openBrowser,
      proxy: {
        "/api": {
          target: apiProxyTarget,
          changeOrigin: true,
        },
      },
    },
  };
});

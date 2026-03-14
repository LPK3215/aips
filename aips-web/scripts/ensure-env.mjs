import { existsSync } from "node:fs";
import { copyFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const projectDir = path.resolve(scriptDir, "..");
const envFile = path.join(projectDir, ".env");
const templateFile = path.join(projectDir, ".env.example");

if (existsSync(envFile)) {
  process.exit(0);
}

if (!existsSync(templateFile)) {
  console.warn("[aips-web] 未找到 .env.example，跳过生成 .env。");
  process.exit(0);
}

try {
  await copyFile(templateFile, envFile);
  console.log("[aips-web] 已生成配置文件：.env（可按需修改）");
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`[aips-web] 生成 .env 失败：${message}`);
  process.exitCode = 1;
}

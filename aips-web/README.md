# aips-web

`aips-web` 是 AIPS（AI ID Photo Studio）的前端项目，技术栈为 `Vue 3 + TypeScript + Vite + Pinia + Vue Router`。

## 配置

本项目使用 `.env` 作为本地配置文件（默认被 Git 忽略），仓库提供模板：

- `.env.example`（模板）
- `.env`（本地配置，按需修改）

生成本地 `.env`：

- 推荐：在仓库根目录运行 `python init-env.py`
- 或直接运行 `npm run dev` / `npm run build`（若 `.env` 不存在，会从 `.env.example` 自动生成）

## 本地启动（开发）

首次安装依赖：

```bash
npm install
```

启动开发服务：

```bash
npm run dev
```

默认访问：

- 前端地址：`http://127.0.0.1:5173`

## 自检

在 `aips-web/` 目录运行（含 TypeScript 类型检查）：

```bash
npm run build
```

## 构建与部署

构建：

```bash
npm run build
```

构建产物输出到 `dist/`。生产部署说明见：`deploy-frontend.md`。

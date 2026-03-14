# AIPS

AIPS（AI ID Photo Studio）是一个证件照智能处理平台 MVP，采用前后端分离架构：

- 前端子项目：`aips-web`（Vue 3 + TypeScript + Vite + Pinia + Vue Router）
- 后端子项目：`aips-api`（FastAPI + Pillow + OpenCV）

## 命名约定

- 主项目：`AIPS`
- 中文名称：`证件照智能处理平台`
- 英文名称：`AI ID Photo Studio`
- 前端子项目：`aips-web`
- 后端子项目：`aips-api`
- 预留管理端：`aips-admin`

## 目录

```text
aips-api/  FastAPI 图像处理服务
aips-web/  Vue 工作台和结果页
docs/      AIPS 项目文档
```

## 启动

本地开发使用前后端各自独立的 `.env` 配置文件（`.env` 默认被 Git 忽略，仓库提供 `.env.example` 模板）：

- 后端模板：[aips-api/.env.example](aips-api/.env.example)
- 前端模板：[aips-web/.env.example](aips-web/.env.example)

首次使用建议先生成本地 `.env`（再按需修改）：

```bash
python init-env.py
```

默认配置：

- 后端：`http://127.0.0.1:8000`
- 前端：`http://127.0.0.1:5173`

### 启动后端

首次需要先安装依赖：

```bash
cd aips-api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

之后在 `aips-api` 目录直接运行：

```bash
python start-aips.py
```

脚本会自动读取 `.env` 并启动后端服务（若 `.env` 不存在，会从 `.env.example` 自动生成）。

默认地址：`http://127.0.0.1:8000`

### 启动前端

首次需要先安装依赖：

```bash
cd aips-web
npm install
```

之后启动开发服务：

```bash
cd aips-web
npm run dev
```

默认地址：`http://127.0.0.1:5173`

`npm run dev` 会自动读取本地 `.env`（若不存在，会从 `.env.example` 自动生成），按其中配置设置前端地址、开发代理和 API 基地址。

## 自检（建议发布/交付前跑一次）

后端测试：

```bash
cd aips-api
.venv\Scripts\python.exe -m pytest -q
```

前端构建检查（含 TypeScript 类型检查）：

```bash
cd aips-web
npm run build
```

> 若你在命令行用 `curl`/`Invoke-WebRequest` 访问本地接口出现 `502 Bad Gateway`，通常是系统代理导致；可设置 `NO_PROXY=127.0.0.1,localhost`，或使用 `curl --noproxy '*' http://127.0.0.1:8000/api/v1/health` 进行验证。

## 当前冻结基线（2026-03-14）

本轮交付以“现有功能稳定可用”为目标，当前冻结范围如下：

- 工作台：上传、规格选择、自定义尺寸、裁剪构图、导出参数、结果预览与下载
- 批量页：批量上传、统一规格处理、ZIP 打包下载
- 工具页：图片缩放、清晰增强
- 结果页：结果查看、下载、打印排版
- 后端任务流：提交任务、轮询状态、查询详情、文件清理

本次冻结前已完成的验证：

- `cd aips-api && .venv\Scripts\python.exe -m pytest`
- `cd aips-web && npm run build`
- `cd aips-web && npx eslint . --ext .vue,.js,.jsx,.cjs,.mjs,.ts,.tsx,.cts,.mts`
- 浏览器烟测：工作台上传/导出、结果页、批量导出、图片缩放、清晰增强

后续如果继续加功能，应以这个冻结基线为起点增量开发。

发布执行时，直接使用：`docs/release-checklist.md`

## 当前已实现

- 图片上传与校验
- 证件照规格预设
- 自定义单位换算
- 真实裁剪/缩放/居中构图
- 亮度、对比度、饱和度、锐化、模糊
- 输出格式、DPI、背景色、文件名控制
- JPEG 目标大小逼近
- 结果预览与下载
- 批量上传、批量自动居中导出
- 批量结果 ZIP 打包下载（含 manifest.json 参数说明）
- 打印排版图生成（A4/6寸）
- 后端基础测试

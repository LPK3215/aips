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

本地开发使用前后端各自独立的 `.env` 配置文件：

- 后端配置：[aips-api/.env](aips-api/.env)
- 前端配置：[aips-web/.env](aips-web/.env)

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

脚本会自动读取 `.env` 并启动后端服务。

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

`npm run dev` 会自动读取 [aips-web/.env](aips-web/.env)，按其中配置设置前端地址、开发代理和 API 基地址。

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

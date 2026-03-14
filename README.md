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

## 启动 aips-api

```powershell
cd aips-api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

默认地址：`http://127.0.0.1:8000`

## 启动 aips-web

```powershell
cd aips-web
npm install
npm run dev
```

默认地址：`http://127.0.0.1:5173`

前端开发环境已配置 `/api` 代理到后端 `8000` 端口。

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

# aips-api

`aips-api` 是 AIPS（AI ID Photo Studio）的后端服务，技术栈为 `FastAPI + Pillow + OpenCV`。

## 配置

本项目使用 `.env` 作为本地配置文件（默认被 Git 忽略），仓库提供模板：

- `.env.example`（模板）
- `.env`（本地配置，按需修改）

生成本地 `.env`：

- 推荐：在仓库根目录运行 `python init-env.py`
- 或直接运行 `python start-aips.py`（若 `.env` 不存在，会从 `.env.example` 自动生成）

## 本地启动（开发）

建议 Python 3.10+。

首次安装依赖：

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

启动服务：

```bash
python start-aips.py
```

默认访问：

- 接口基地址：`http://127.0.0.1:8000`
- 健康检查：`GET /api/v1/health`
- OpenAPI：`/docs`

## 自检

在 `aips-api/` 目录运行：

```bash
.venv\Scripts\python.exe -m pytest -q
```

## 部署

生产部署与 Nginx/systemd 示例见：`deploy-backend.md`。

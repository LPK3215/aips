# aips-api 部署与启动说明

## 1. 项目说明

`aips-api` 是 AIPS 的后端服务，技术栈为 `FastAPI + Pillow + OpenCV`。

当前默认约定：

- 本地启动端口：`8000`
- API 前缀：`/api/v1`
- 健康检查：`GET /api/v1/health`
- 存储目录：`aips-api/storage/`

后端启动时会自动创建以下目录：

- `storage/uploads/`
- `storage/results/`
- `storage/tasks/`
- `storage/temp/`

## 2. 本地启动

建议使用 Python 3.10 及以上版本。

### 2.1 推荐方式：直接运行启动文件

后端配置文件：

- [aips-api/.env](.env)

首次准备依赖：

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

### 2.2 备用方式

```powershell
cd aips-api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.run_dev
```

启动后访问：

- 接口基地址：`http://127.0.0.1:8000`
- 健康检查：`http://127.0.0.1:8000/api/v1/health`
- OpenAPI 文档：`http://127.0.0.1:8000/docs`

健康检查返回示例：

```json
{"status":"ok"}
```

`python -m app.run_dev` 会自动读取 [.env](.env) 中的后端地址和端口，不需要再手动写 `--host`、`--port`。

后端 `.env` 主要字段：

```dotenv
AIPS_API_HOST=127.0.0.1
AIPS_API_PORT=8000
AIPS_WEB_HOST=127.0.0.1
AIPS_WEB_PORT=5173
# AIPS_CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

说明：

- `AIPS_API_HOST` 和 `AIPS_API_PORT` 控制 `uvicorn` 启动地址
- `AIPS_WEB_HOST` 和 `AIPS_WEB_PORT` 用于生成默认开发 CORS
- `AIPS_CORS_ORIGINS` 可选，设置后会覆盖自动生成的 CORS 列表

## 3. 生产环境直接启动

如果先要在服务器上手动验证服务是否正常，可以直接启动：

```bash
cd /path/to/aips/aips-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

说明：

- 生产环境建议先绑定到 `127.0.0.1:8000`
- 对外访问通过 Nginx 或其他反向代理转发
- `storage/` 目录建议放在持久化磁盘上，不要依赖临时目录

## 4. systemd 托管示例

适用于 Linux 服务器。

示例文件：`/etc/systemd/system/aips-api.service`

```ini
[Unit]
Description=AIPS API
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/aips/aips-api
ExecStart=/path/to/aips/aips-api/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
```

启用方式：

```bash
sudo systemctl daemon-reload
sudo systemctl enable aips-api
sudo systemctl start aips-api
sudo systemctl status aips-api
```

查看日志：

```bash
sudo journalctl -u aips-api -f
```

## 5. Nginx 反向代理示例

如果前端和后端走同一域名，推荐使用下面这种方式：

```nginx
server {
    listen 80;
    server_name example.com;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

这样前端可以直接请求同域名下的 `/api/v1/...`，不需要额外改前端代码。

## 6. 部署注意事项

### 6.1 CORS

当前代码里只放行了本地开发地址：

- `http://127.0.0.1:5173`
- `http://localhost:5173`

如果你修改了 [.env](.env) 里的 `AIPS_WEB_HOST` 或 `AIPS_WEB_PORT`，开发环境 CORS 会同步跟着更新。

如果生产环境前后端不是同域部署，需要修改 [app/main.py](app/main.py) 中的 `allow_origins`。

如果生产环境通过同域名 Nginx 反向代理访问，通常不需要额外改 CORS。

### 6.2 存储清理

服务启动后会自动运行清理任务，清理历史上传、结果和临时文件。默认存储 TTL 为 24 小时。

如果后续要保留更长时间的结果文件，需要调整 [app/core/config.py](app/core/config.py) 中的配置。

### 6.3 反向代理路径

前端请求路径默认是相对路径 `/api/v1/...`。因此生产环境不要把 API 挂到别的路径前缀，除非同步修改前端构建参数。

## 7. 上线检查清单

- `aips-api` 服务已正常启动
- `GET /api/v1/health` 返回 `{"status":"ok"}`
- `storage/` 目录可写
- 反向代理已正确转发 `/api/`
- 上传、处理、下载流程至少手动验证一次

# aips-web 部署与启动说明

## 1. 项目说明

`aips-web` 是 AIPS 的前端项目，技术栈为 `Vue 3 + TypeScript + Vite + Pinia + Vue Router`。

当前默认约定：

- 本地开发端口：`5173`
- 开发环境通过 Vite 代理 `/api` 到 `http://127.0.0.1:8000`
- 生产环境默认使用相对路径请求 `/api/v1/...`

前端代码中的 API 基地址规则如下：

- 未设置 `VITE_API_BASE_URL` 时，直接请求同域名下的 `/api/v1/...`
- 设置了 `VITE_API_BASE_URL` 时，请求 `${VITE_API_BASE_URL}/api/v1/...`

## 2. 本地启动

### 2.1 启动前端

前端配置文件：

- [aips-web/.env](.env)

首次准备依赖：

```bash
cd aips-web
npm install
```

之后启动开发服务：

```bash
npm run dev
```

启动后默认访问：

- 前端地址：`http://127.0.0.1:5173`

注意：

- 本地调试前，建议先启动 `aips-api`（进入 `aips-api/` 目录运行 `python start-aips.py`）
- Vite 会自动读取 [.env](.env)
- `/api` 代理目标会自动指向前端 `.env` 里配置的 `VITE_API_PROXY_TARGET`

前端 `.env` 主要字段：

```dotenv
VITE_APP_HOST=127.0.0.1
VITE_APP_PORT=5173
VITE_API_PROXY_TARGET=http://127.0.0.1:8000
VITE_API_BASE_URL=
VITE_DEV_OPEN_BROWSER=true
```

说明：

- `VITE_APP_HOST` 和 `VITE_APP_PORT` 控制 `npm run dev` 的前端地址
- `VITE_API_PROXY_TARGET` 控制开发环境 `/api` 代理目标
- `VITE_API_BASE_URL` 控制浏览器实际请求的 API 基地址
- `VITE_DEV_OPEN_BROWSER` 控制开发模式是否自动打开浏览器

## 3. 生产构建

```bash
cd /path/to/aips/aips-web
npm install
npm run build
```

构建产物输出到：

- `aips-web/dist/`

本地预览构建结果：

```bash
npm run preview
```

`preview` 只适合验包，不建议直接作为生产服务。

## 4. 推荐部署方式：同域部署

这是当前仓库最省事、也最适合现有代码的方式。

部署思路：

1. `aips-web` 构建出静态文件
2. Nginx 直接托管 `dist/`
3. Nginx 将 `/api/` 反向代理到 `aips-api`

这样有两个好处：

- 前端不需要额外设置 `VITE_API_BASE_URL`
- 后端当前的 CORS 配置也不需要为生产单独放开新域名

Nginx 示例：

```nginx
server {
    listen 80;
    server_name example.com;

    root /path/to/aips/aips-web/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

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

其中 `try_files $uri $uri/ /index.html;` 是单页应用路由回退配置，不能省。

## 5. 分域部署方式

如果前端和后端不走同一域名，构建前需要设置 `VITE_API_BASE_URL`。

Linux/macOS 示例：

```bash
cd /path/to/aips/aips-web
export VITE_API_BASE_URL=https://api.example.com
npm install
npm run build
```

PowerShell 示例：

```powershell
cd aips-web
$env:VITE_API_BASE_URL="https://api.example.com"
npm install
npm run build
```

注意：

- 这个值在构建时生效，不是运行时再读取
- 如果切换后端域名，需要重新构建前端
- 分域部署时，后端也要同步放开对应的 CORS 域名

## 6. 静态资源发布步骤

如果使用 Nginx 托管，可以按下面流程发布：

```bash
cd /path/to/aips/aips-web
npm install
npm run build
rsync -av --delete dist/ /var/www/aips-web/
```

然后把 Nginx 的 `root` 指向 `/var/www/aips-web/`。

## 7. 上线检查清单

- `npm run build` 已成功完成
- `dist/` 已发布到 Web 根目录
- 页面刷新任意前端路由不会返回 404
- 页面能正常请求 `/api/v1/presets`
- 上传、处理、结果页、批量导出至少验证一次
- 如果是分域部署，`VITE_API_BASE_URL` 和后端 CORS 已同步配置

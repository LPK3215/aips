# AIPS 发布清单

## 1. 当前发布基线

- 发布目标：`AIPS MVP`
- 当前代码基线日期：`2026-03-14`
- 建议版本号：`v0.1.0`

本次发布覆盖范围：

- 工作台：上传、规格选择、自定义尺寸、裁剪构图、导出参数、结果预览与下载
- 批量页：批量上传、统一规格处理、ZIP 打包下载
- 工具页：图片缩放、清晰增强
- 结果页：结果查看、下载、打印排版
- 后端任务流：提交任务、轮询状态、查询详情、文件清理

## 2. 发布前确认

### 2.1 代码与文档

- 当前冻结基线已确认
- `README.md` 已更新
- `docs/id-photo-project-plan.md` 已更新
- 前后端部署文档可直接使用：
  - `aips-api/deploy-backend.md`
  - `aips-web/deploy-frontend.md`

### 2.2 已完成验证

后端测试：

```powershell
cd aips-api
.venv\Scripts\python.exe -m pytest
```

前端构建：

```powershell
cd aips-web
npm run build
```

前端静态检查：

```powershell
cd aips-web
npx eslint src --ext .vue,.js,.jsx,.cjs,.mjs,.ts,.tsx,.cts,.mts
```

浏览器烟测：

- 工作台上传 / 导出 / 结果页
- 批量导出
- 图片缩放
- 清晰增强

## 3. 发布顺序

建议顺序：

1. 发布后端
2. 检查后端健康状态
3. 发布前端静态资源
4. 做线上烟测
5. 再决定是否打版本标签

原因：

- 前端依赖后端接口
- 后端先稳定，前端上线后才能立即可用

## 4. 后端发布步骤

参考：`aips-api/deploy-backend.md`

核心步骤：

```bash
cd /path/to/aips/aips-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

如使用 `systemd`：

```bash
sudo systemctl daemon-reload
sudo systemctl restart aips-api
sudo systemctl status aips-api
```

发布后立即检查：

```bash
curl --noproxy '*' http://127.0.0.1:8000/api/v1/health
```

预期结果：

```json
{"status":"ok"}
```

## 5. 前端发布步骤

参考：`aips-web/deploy-frontend.md`

构建：

```bash
cd /path/to/aips/aips-web
npm install
npm run build
```

发布静态资源：

```bash
rsync -av --delete dist/ /var/www/aips-web/
```

如果前后端同域部署：

- Nginx 托管 `dist/`
- Nginx 反代 `/api/` 到 `aips-api`

如果前后端分域部署：

- 构建前设置 `VITE_API_BASE_URL`
- 同步检查后端 `CORS`

## 6. 线上烟测清单

发布完成后，至少手动验证以下流程：

### 6.1 工作台

- 打开首页
- 上传一张图片
- 切换一个预设
- 修改一次尺寸单位
- 生成预览
- 下载结果
- 进入结果页

### 6.2 批量导出

- 上传 2 张图片
- 执行批量导出
- 下载 ZIP

### 6.3 常用工具

- 图片缩放：上传 → 导出
- 清晰增强：上传 → 导出

### 6.4 结果页

- 查看结果预览
- 下载图片
- 生成打印排版图

## 7. 回滚策略

如果发布后发现问题，按下面顺序回滚：

### 7.1 前端问题

- 回滚 Nginx 静态目录到上一版 `dist/`
- 保留后端不动

### 7.2 后端问题

- 回滚 `aips-api` 代码目录到上一版
- 重启 `aips-api` 服务
- 再检查 `/api/v1/health`

### 7.3 数据与文件

当前版本以本地文件存储为主：

- `storage/uploads/`
- `storage/results/`
- `storage/tasks/`
- `storage/temp/`

回滚前不要误删 `storage/`，避免影响已生成结果和任务状态。

## 8. 发布产出物

本次发布建议至少保留以下内容：

- 发布时的代码版本号或 Git tag
- 前端构建产物对应版本
- 后端部署版本
- 本文档：`docs/release-checklist.md`
- 部署说明：
  - `aips-api/deploy-backend.md`
  - `aips-web/deploy-frontend.md`

## 9. 发布完成判定

满足以下条件即可判定“本次发布完成”：

- 后端健康检查正常
- 前端首页可访问
- 工作台主流程可用
- 批量导出可用
- 缩放与增强工具可用
- 没有阻塞级报错

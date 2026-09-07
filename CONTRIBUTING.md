# 贡献指南

感谢您关注 AIPS！请阅读以下指南参与贡献。

## 开发环境搭建

请先阅读 [README.md](./README.md) 了解项目架构和安装步骤。

## 分支策略

- `main` — 稳定发布分支
- `feature/*` — 新功能分支
- `fix/*` — Bug 修复分支

## 提交规范

| 前缀 | 用途 |
|---|---|
| `feat:` | 新功能 |
| `fix:` | Bug 修复 |
| `docs:` | 文档更新 |
| `refactor:` | 代码重构 |
| `chore:` | 构建/工具变更 |
| `test:` | 测试相关 |

## Pull Request 流程

1. Fork 本仓库
2. 从 `main` 分支创建特性分支
3. 编写代码并确保前后端可正常启动
4. 提交 PR，描述变更内容和动机

## 代码规范

### 后端（Python / FastAPI）

- 使用 Python 3.10+ 风格
- 遵循 PEP 8 规范
- 不要提交 `.env` 文件

### 前端（Vue 3 / TypeScript）

- 使用 `<script setup lang="ts">` 语法
- 提交前确保 `npm run dev` 可正常启动

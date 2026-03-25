# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用命令

### 后端开发 (backend/)

```bash
# 安装依赖
uv sync

# 启动开发服务器
uv run main.py run --env=dev

# 启动生产服务器
uv run main.py run --env=prod

# 生成数据库迁移脚本 (Alembic autogenerate)
uv run main.py revision --env=dev

# 应用数据库迁移
uv run main.py upgrade --env=dev

# 代码检查
uv run ruff check

# 代码检查并自动修复
uv run ruff check --fix
```

### 前端开发 (frontend/)

```bash
# 安装依赖 (强制使用 pnpm)
pnpm install

# 启动开发服务器
pnpm run dev

# 构建生产版本
pnpm run build

# 类型检查
pnpm run ts:check

# 代码检查与格式化
pnpm run lint
```

## 环境配置

### 后端环境

1. 复制配置模板: `cp backend/env/.env.dev.example backend/env/.env.dev`
2. 修改数据库连接信息 (DATABASE_*)
3. 修改 Redis 连接信息 (REDIS_*)
4. 修改 AI 模型配置 (OPENAI_*)

### 前端环境

1. 复制配置模板: `cp frontend/.env.development.example frontend/.env.development`
2. 修改 API 地址 (VITE_API_BASE_URL)
3. 修改 WebSocket 端点 (VITE_APP_WS_ENDPOINT)

## 开发规范

> 详细开发规范请使用 `fastapiadmin-dev` skill

### 操作日志

使用 `OperationLogRoute` 自动记录操作日志:

```python
from app.core.router_class import OperationLogRoute

router = APIRouter(
    route_class=OperationLogRoute,
    prefix="/feature",
    tags=["功能模块"]
)
```

### 响应格式

统一使用 `SuccessResponse` 或 `ErrorResponse`:

```python
from app.common.response import SuccessResponse, ErrorResponse

return SuccessResponse(data=result)
return ErrorResponse(msg="操作失败")
```

## 数据库迁移

项目使用 Alembic 进行数据库版本管理:

- **已有数据库初始化**: 导入 SQL 文件后执行 `alembic stamp head` 建立版本基线
- **模型变更**: `uv run main.py revision --env=dev` 自动生成迁移
- **应用迁移**: `uv run main.py upgrade --env=dev`

**注意**: SQL 导入和 Alembic 迁移是互斥的初始化方式。

## Docker 数据库操作

数据库（PostgreSQL、Redis）运行在 Docker 容器中。

### 查看数据库容器

```bash
docker ps | grep -E 'postgres|redis'
```

### 执行 SQL 文件

```bash
# 使用 docker exec 执行 psql
docker exec -i <postgres_container_name> psql -U root -d tc-platform < backend/path/to/file.sql

# 示例：执行模块菜单初始化
docker exec -i tc-platform-postgres psql -U root -d tc-platform < backend/app/plugin/module_modbus/init_menu.sql
```

### 连接数据库交互式终端

```bash
# PostgreSQL
docker exec -it <postgres_container_name> psql -U root -d tc-platform

# Redis
docker exec -it <redis_container_name> redis-cli -a <password>
```

## 技术栈版本

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端框架 | FastAPI | 0.115.2 |
| ORM | SQLAlchemy | 2.0.45 |
| 数据迁移 | Alembic | 1.15.1 |
| 前端框架 | Vue3 | 3.5.x |
| 构建工具 | Vite | 6.x |
| UI 组件 | Element Plus | 2.11.x |
| 包管理 | pnpm | 9.x |
| 数据库 | MySQL/PostgreSQL | 8.0+/17+ |
| 缓存 | Redis | 7.0+ |
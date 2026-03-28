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
2. 修改数据库连接信息 (DATABASE\_\*)
3. 修改 Redis 连接信息 (REDIS\_\*)
4. 修改 AI 模型配置 (OPENAI\_\*)

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

### WebSocket 路由规范

**规则：WebSocket 路由必须放在独立的 `ws.py` 文件中，不与 `controller.py` 混合。**

原因：
- 动态路由发现 (`app/core/discover.py`) 只扫描 `controller.py` 文件
- WebSocket 路由需要手动注册到根应用，避免路径前缀问题
- AI 模块已采用此模式 (`app/plugin/module_ai/chat/ws.py`)

示例结构：
```
app/plugin/module_xxx/
├── controller.py    # HTTP API 路由（自动发现）
└── ws.py            # WebSocket 路由（手动注册）
```

在 `init_app.py` 中手动注册：
```python
from app.plugin.module_xxx.ws import WS_Xxx

app.include_router(
    router=WS_Xxx,
    dependencies=[Depends(WebSocketRateLimiter(times=1, seconds=5))]
)
```

前端连接方式：
```typescript
// 使用环境变量直接连接后端
const WS_URL = import.meta.env.VITE_APP_WS_ENDPOINT;  // ws://127.0.0.1:9000
const url = new URL("/api/v1/xxx/ws", WS_URL);
url.searchParams.append("token", token);
```

### 数据库时间字段规范

**规则：时间字段的使用必须与数据库列定义保持一致。**

注意点：
1. PostgreSQL 的 `DateTime` 不带 `timezone=True` 是 naive 类型，带 `timezone=True` 是 aware 类型
2. **关键**：如果数据库列是 naive 类型，代码必须使用 `datetime.now()`；如果列是 aware 类型，才使用 `datetime.now(timezone.utc)`
3. asyncpg 会严格检查类型一致性，混合使用 naive 和 aware datetime 会抛出 `DBAPIError: can't subtract offset-naive and offset-aware datetimes`

```python
# ❌ 错误：数据库列是 naive，代码使用 aware
# asyncpg 会报错：can't subtract offset-naive and offset-aware datetimes
last_seen = datetime.now(timezone.utc)  # aware
# 数据库列定义：DateTime (naive)

# ✅ 正确：保持一致
last_seen = datetime.now()  # naive，与数据库列一致
```

**检查方法**：查看模型定义中的 `DateTime` 是否带有 `timezone=True` 参数。

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
docker exec -i postgres psql -U root -d tc-platform < backend/app/plugin/module_modbus/init_menu.sql
```

### 连接数据库交互式终端

```bash
# PostgreSQL
docker exec -it <postgres_container_name> psql -U root -d tc-platform

# Redis
docker exec -it <redis_container_name> redis-cli -a <password>
```

## 技术栈版本

| 层级     | 技术             | 版本     |
| -------- | ---------------- | -------- |
| 后端框架 | FastAPI          | 0.115.2  |
| ORM      | SQLAlchemy       | 2.0.45   |
| 数据迁移 | Alembic          | 1.15.1   |
| 前端框架 | Vue3             | 3.5.x    |
| 构建工具 | Vite             | 6.x      |
| UI 组件  | Element Plus     | 2.11.x   |
| 包管理   | pnpm             | 9.x      |
| 数据库   | MySQL/PostgreSQL | 8.0+/17+ |
| 缓存     | Redis            | 7.0+     |

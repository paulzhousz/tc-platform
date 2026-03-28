# Proposal: Modbus 设备控制模块迁移

## Intent

将现有 `speech2txt` 项目中的 Modbus 设备控制模块完整迁移到 `tc-platform` (FastAPI Admin) 框架中，实现工业 PLC 设备的自然语言控制能力。

## Scope

### 包含功能

| 功能模块 | 描述 |
|---------|------|
| 设备管理 | PLC 设备 CRUD + 点位 CRUD |
| 设备连接控制 | Modbus TCP 连接池 + 轮询服务 |
| 自然语言控制 | LLM Agent + 流式对话 (SSE) |
| 操作日志 | CommandLog 记录与查询 |
| 待确认操作 | PendingConfirm 管理 |
| 聊天历史 | 会话存储与加载 |
| 语音输入 | FunASR WebSocket 集成 |
| WebSocket | 实时状态推送 |

### 排除功能

- 用户权限管理（使用系统公共模块）
- HTTP 请求审计日志（使用系统 OperationLogRoute，自动记录所有 API 调用）

> **注意**：本模块包含独立的 PLC 操作审计日志（CommandLog），用于记录设备读写操作的详细信息，与系统的 HTTP 请求审计是两个独立的日志体系。

## Approach

### 后端迁移策略

1. **适配 FastAPI Admin 框架规范**
   - 数据模型继承 `ModelMixin` / `UserMixin`
   - 路由使用 `OperationLogRoute` 自动记录操作日志
   - 权限检查使用 `AuthPermission` 依赖
   - 响应格式使用 `SuccessResponse` / `ErrorResponse`

2. **配置项迁移**
   - 所有配置项使用 `MODBUS_` 前缀
   - LLM 相关配置使用 `MODBUS_LLM_` 前缀

3. **模块结构**
   ```
   backend/app/plugin/module_modbus/
   ├── __init__.py
   ├── models.py                  # 共享数据模型
   ├── schemas.py                 # Pydantic 验证模型（统一）
   ├── modbus_simulator.py        # Modbus 模拟器（测试用）
   ├── device/                    # 设备管理
   │   ├── __init__.py
   │   ├── controller.py          # 设备 API 路由
   │   ├── crud.py                # 设备 CRUD 操作
   │   └── service.py             # 设备业务逻辑
   ├── control/                   # 控制操作
   │   ├── __init__.py
   │   ├── controller.py          # 控制 API 路由（含日志、待确认、聊天历史）
   │   ├── ws.py                  # WebSocket 路由（独立文件）
   │   ├── schemas.py             # 控制模块 Schema（如需要）
   │   ├── crud/                  # CRUD 操作层
   │   │   ├── __init__.py
   │   │   ├── command_log.py
   │   │   ├── chat_history.py
   │   │   └── pending_confirm.py
   │   └── services/
   │       ├── __init__.py
   │       ├── plc_service.py            # 异步 PLC 操作
   │       ├── sync_plc_service.py       # 同步 PLC 操作（Agent 用）
   │       ├── agent_service.py          # LLM Agent 服务
   │       ├── connection_pool.py        # Modbus 连接池
   │       ├── client_factory.py         # Modbus 客户端工厂
   │       ├── poll_service.py           # 状态轮询服务
   │       ├── websocket_service.py      # WebSocket 消息服务
   │       ├── cleanup_service.py        # 清理服务
   │       ├── config_service.py         # 配置服务
   │       ├── command_log_service.py    # 命令日志服务
   │       ├── chat_history_service.py   # 聊天历史服务
   │       └── pending_confirm_service.py # 待确认操作服务
   └── init_menu.sql             # 菜单初始化 SQL
   ```

### 前端迁移策略

1. **UI 组件库适配**
   - Ant Design Vue → Element Plus
   - 组件映射详见设计文档

2. **模块结构**
   ```
   frontend/src/
   ├── api/module_modbus/         # API 调用
   │   ├── device.ts              # 设备管理 API
   │   ├── control.ts             # 控制操作 API
   │   ├── log.ts                 # 日志 API
   │   └── index.ts               # 统一导出
   ├── store/modules/modbus.store.ts  # Pinia 状态管理
   ├── composables/modbus/        # 组合式函数
   │   ├── index.ts               # 统一导出
   │   ├── use-modbus-ws.ts       # Modbus WebSocket
   │   ├── use-funasr-ws.ts       # FunASR 语音识别 WebSocket
   │   └── use-typewriter.ts      # 打字机效果
   └── views/module_modbus/       # 页面组件
       ├── device/index.vue       # 设备管理页面
       ├── control/index.vue      # AI 控制页面
       └── log/index.vue          # 操作日志页面
   ```

## Success Criteria

1. 所有 8 个功能模块正常工作
2. 后端 API 通过权限验证
3. 前端页面使用 Element Plus 组件正确渲染
4. 流式对话、WebSocket、语音输入功能正常
5. 配置项可通过环境变量配置
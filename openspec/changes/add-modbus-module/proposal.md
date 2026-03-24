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
- 操作日志管理（使用系统 OperationLogRoute）

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
   ├── device/                    # 设备管理
   │   ├── __init__.py
   │   ├── controller.py
   │   ├── crud.py
   │   ├── model.py
   │   ├── schema.py
   │   └── service.py
   ├── control/                   # 控制操作
   │   ├── __init__.py
   │   ├── controller.py
   │   ├── schema.py
   │   └── services/
   │       ├── __init__.py
   │       ├── plc_service.py
   │       ├── agent_service.py
   │       ├── connection_pool.py
   │       ├── client_factory.py
   │       ├── poll_service.py
   │       ├── websocket_service.py
   │       └── cleanup_service.py
   ├── log/                       # 操作日志
   │   └── ...
   ├── pending/                   # 待确认操作
   │   └── ...
   └── models.py                  # 共享数据模型
   ```

### 前端迁移策略

1. **UI 组件库适配**
   - Ant Design Vue → Element Plus
   - 组件映射详见设计文档

2. **模块结构**
   ```
   frontend/src/
   ├── api/module_modbus/         # API 调用
   │   ├── device.ts
   │   ├── control.ts
   │   └── log.ts
   ├── store/modules/modbus/      # Pinia 状态管理
   │   └── index.ts
   ├── composables/modbus/        # 组合式函数
   │   ├── use-modbus-ws.ts
   │   └── use-funasr-ws.ts
   └── views/module_modbus/       # 页面组件
       ├── device/
       ├── control/
       └── log/
   ```

## Success Criteria

1. 所有 8 个功能模块正常工作
2. 后端 API 通过权限验证
3. 前端页面使用 Element Plus 组件正确渲染
4. 流式对话、WebSocket、语音输入功能正常
5. 配置项可通过环境变量配置
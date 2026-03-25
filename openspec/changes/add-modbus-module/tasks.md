# Modbus 控制模块实施任务清单

## Phase 1: 后端基础设施 (P0) ✅ 已完成

> 依赖：无

### 1.1 配置与依赖
- [x] 在 `backend/app/config/setting.py` 添加 Modbus 配置项
- [x] 在 `backend/env/.env.dev.example` 添加配置示例
- [x] 添加依赖：`pymodbus`, `langchain-openai`, `langchain-core`

### 1.2 数据模型
- [x] 创建 `backend/app/plugin/module_modbus/__init__.py`
- [x] 创建 `backend/app/plugin/module_modbus/models.py`
  - [x] DeviceModel
  - [x] TagPointModel
  - [x] CommandLogModel
  - [x] PendingConfirmModel
  - [x] AgentSessionModel
  - [x] ChatHistoryModel

### 1.3 数据库迁移
- [x] 生成 Alembic 迁移脚本
- [x] 执行数据库迁移

### 1.4 配置文件（LLM Agent 核心依赖）
- [x] 创建 `backend/config/modbus_system_prompt.md` - 系统提示词
- [x] 创建 `backend/config/modbus_quick_commands.json` - 快捷指令

---

## Phase 2: 后端核心服务 (P0) ✅ 已完成

> 依赖：Phase 1 完成

### 2.1 连接池服务
- [x] 创建 `control/services/client_factory.py` - Modbus 客户端工厂
- [x] 创建 `control/services/connection_pool.py` - 连接池管理

### 2.2 PLC 操作服务
- [x] 创建 `control/services/plc_service.py` - 异步版本
- [x] 创建 `control/services/sync_plc_service.py` - 同步版本（用于 Agent）
  - [x] read() - 读取点位
  - [x] write() - 写入点位
  - [x] adjust() - 调整参数
  - [x] search_devices() - 设备搜索
  - [x] search_tags_in_device() - 点位搜索

### 2.3 LLM Agent 服务
- [x] 创建 `control/services/agent_service.py`
  - [x] LangChain 工具定义（同步工具函数）
  - [x] chat() - 同步对话
  - [x] stream_chat() - 流式对话

### 2.4 辅助服务
- [x] 创建 `control/services/poll_service.py` - 轮询服务
- [x] 创建 `control/services/websocket_service.py` - WebSocket 服务
- [x] 创建 `control/services/cleanup_service.py` - 清理服务

---

## Phase 3: 后端 API 路由 (P0) ✅ 已完成

> 依赖：Phase 1、Phase 2 完成

### 3.1 数据验证模型
- [x] 创建 `schemas.py` - Pydantic 验证模型

### 3.2 API 控制器（合并到 controller.py）
- [x] 创建 `control/controller.py` - 统一 API 路由
  - [x] 设备管理 API (DeviceRouter)
    - [x] GET /device/list
    - [x] GET /device/{id}
    - [x] POST /device
    - [x] PUT /device/{id}
    - [x] DELETE /device/{id}
    - [x] GET /device/{id}/tags
    - [x] POST /device/{id}/tags
  - [x] 控制操作 API (ControlRouter)
    - [x] POST /connect
    - [x] POST /disconnect
    - [x] GET /connection-status
    - [x] POST /chat
    - [x] POST /chat/stream (SSE)
    - [x] POST /read
    - [x] POST /write
    - [x] POST /adjust
    - [x] GET /quick-commands
  - [x] 操作日志 API (LogRouter)
    - [x] GET /logs
    - [x] GET /logs/{id}
  - [x] 待确认操作 API (PendingRouter)
    - [x] GET /pending
    - [x] POST /pending/{id}/confirm
    - [x] POST /pending/{id}/reject
  - [x] 聊天历史 API
    - [x] GET /chat-history
    - [x] GET /chat-history/{id}
    - [x] DELETE /chat-history/{id}

### 3.3 WebSocket 路由
- [ ] 创建 WebSocket 端点 `/ws/modbus`
- [ ] 实现连接认证（Token 验证）
- [ ] 实现消息广播逻辑
- [ ] 在 `init_app.py` 中注册 WebSocket 路由

---

## Phase 4: 前端基础设施 (P0)

> 依赖：Phase 3 完成

### 4.1 API 层
- [ ] 创建 `frontend/src/api/module_modbus/device.ts`
- [ ] 创建 `frontend/src/api/module_modbus/control.ts`
- [ ] 创建 `frontend/src/api/module_modbus/log.ts`
- [ ] 创建 `frontend/src/api/module_modbus/index.ts` - 导出

### 4.2 状态管理
- [ ] 创建 `frontend/src/store/modules/modbus/index.ts`
  - [ ] devices, tagPoints 状态
  - [ ] messages, sessionId 状态
  - [ ] chatHistory 状态
  - [ ] loadDevices, loadTagPoints actions
  - [ ] sendMessage, sendMessageStream actions
  - [ ] WebSocket 状态管理

### 4.3 组合式函数
- [ ] 创建 `frontend/src/composables/modbus/use-modbus-ws.ts`
- [ ] 创建 `frontend/src/composables/modbus/use-funasr-ws.ts`

---

## Phase 5: 前端页面组件 (P0)

> 依赖：Phase 4 完成

### 5.1 设备管理页面
- [ ] 创建 `frontend/src/views/module_modbus/device/index.vue`
- [ ] 实现设备列表表格
- [ ] 实现设备 CRUD 弹窗
- [ ] 实现点位管理抽屉

### 5.2 控制页面
- [ ] 创建 `frontend/src/views/module_modbus/control/index.vue`
- [ ] 实现设备树组件（Element Plus el-tree）
- [ ] 实现聊天面板
- [ ] 实现消息列表（支持 Markdown 渲染）
- [ ] 实现输入框（支持语音按钮）
- [ ] 实现快捷指令按钮
- [ ] 实现设备详情抽屉

### 5.3 操作日志页面
- [ ] 创建 `frontend/src/views/module_modbus/log/index.vue`
- [ ] 实现日志列表表格
- [ ] 实现日志详情弹窗

---

## Phase 6: 前端高级功能 (P1)

> 依赖：Phase 5 完成

### 6.1 流式对话
- [ ] 实现 SSE 客户端逻辑
- [ ] 实现打字机效果
- [ ] 实现中断生成功能

### 6.2 语音输入
- [ ] 实现 AudioWorklet 处理器
- [ ] 实现 FunASR WebSocket 连接
- [ ] 实现实时识别结果预览
- [ ] 实现自动静音检测

### 6.3 WebSocket 实时通信
- [ ] 实现 WebSocket 连接管理
- [ ] 实现设备状态实时更新
- [ ] 实现断线重连机制

---

## Phase 7: 路由与菜单 (P0)

> 依赖：Phase 5 完成

### 7.1 前端路由
- [ ] 添加 `/modbus/device` 路由
- [ ] 添加 `/modbus/control` 路由
- [ ] 添加 `/modbus/log` 路由

### 7.2 菜单配置
- [ ] 添加侧边栏菜单项
- [ ] 配置菜单权限

---

## Phase 8: 权限配置 (P1)

> 依赖：Phase 1 完成（数据库迁移）

### 8.1 数据库权限数据
- [ ] 添加 modbus 相关权限码
- [ ] 关联权限到角色

---

## Phase 9: 测试与文档 (P2)

> 依赖：所有功能模块完成

### 9.1 后端测试
- [ ] 连接池单元测试
- [ ] PLC 服务单元测试
- [ ] Agent 服务集成测试

### 9.2 文档
- [ ] 更新 CLAUDE.md
- [ ] 添加 API 文档
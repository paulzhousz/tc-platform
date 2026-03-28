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
- [x] 创建 `control/services/websocket_service.py` - WebSocket 消息服务
- [x] 创建 `control/services/cleanup_service.py` - 清理服务
- [x] 创建 `control/services/config_service.py` - 配置服务（Redis 配置读取）

### 2.5 CRUD 服务层
- [x] 创建 `control/crud/command_log.py` - 命令日志 CRUD
- [x] 创建 `control/crud/chat_history.py` - 聊天历史 CRUD
- [x] 创建 `control/crud/pending_confirm.py` - 待确认操作 CRUD

### 2.6 业务服务层
- [x] 创建 `control/services/command_log_service.py` - 命令日志服务
- [x] 创建 `control/services/chat_history_service.py` - 聊天历史服务
- [x] 创建 `control/services/pending_confirm_service.py` - 待确认操作服务

---

## Phase 3: 后端 API 路由 (P0) ✅ 已完成

> 依赖：Phase 1、Phase 2 完成

### 3.1 数据验证模型
- [x] 创建 `schemas.py` - Pydantic 验证模型（根目录统一管理）

### 3.2 设备管理 API（device/controller.py）
- [x] GET /device/list - 获取设备列表
- [x] POST /device/create - 创建设备
- [x] GET /device/detail/{id} - 获取设备详情
- [x] PUT /device/update/{id} - 更新设备
- [x] DELETE /device/delete - 删除设备
- [x] POST /device/{id}/test - 测试设备连接
- [x] GET /device/{device_id}/tag/list - 获取点位列表
- [x] POST /device/{device_id}/tag/create - 创建点位
- [x] PUT /device/tag/update/{tag_id} - 更新点位
- [x] DELETE /device/tag/delete - 删除点位

### 3.3 控制操作 API（control/controller.py）
- [x] POST /control/connect - 连接设备
- [x] POST /control/disconnect - 断开设备
- [x] GET /control/connection-status - 获取连接状态
- [x] GET /control/config - 获取运行时配置
- [x] POST /control/chat - 对话接口
- [x] POST /control/chat/stream - 流式对话接口（SSE）
- [x] POST /control/read - 直接读取 PLC
- [x] POST /control/write - 直接写入 PLC
- [x] GET /control/quick-commands - 获取快捷指令

### 3.4 操作日志 API（control/controller.py - LogRouter）
- [x] GET /log/list - 获取日志列表
- [x] GET /log/detail/{id} - 获取日志详情

### 3.5 待确认操作 API（control/controller.py - PendingRouter）
- [x] GET /pending/list - 获取待确认列表
- [x] POST /pending/{id}/confirm - 确认操作
- [x] POST /pending/{id}/reject - 拒绝操作

### 3.6 聊天历史 API（control/controller.py）
- [x] GET /control/chat-history - 获取历史列表
- [x] GET /control/chat-history/{session_id} - 获取历史详情
- [x] POST /control/chat-history - 保存历史
- [x] DELETE /control/chat-history/{session_id} - 删除历史
- [x] DELETE /control/chat-history - 清空所有历史

### 3.7 WebSocket 路由（control/ws.py）
- [x] 创建 WebSocket 端点 `/api/v1/ws/modbus`
- [x] 实现连接认证（Token 验证）
- [x] 实现消息广播逻辑
- [x] 在 `init_app.py` 中手动注册 WebSocket 路由

---

## Phase 4: 前端基础设施 (P0) ✅ 已完成

> 依赖：Phase 3 完成

### 4.1 API 层
- [x] 创建 `frontend/src/api/module_modbus/device.ts`
- [x] 创建 `frontend/src/api/module_modbus/control.ts`
- [x] 创建 `frontend/src/api/module_modbus/log.ts`
- [x] 创建 `frontend/src/api/module_modbus/index.ts` - 统一导出

### 4.2 状态管理
- [x] 创建 `frontend/src/store/modules/modbus.store.ts`
  - [x] devices, tagPoints 状态
  - [x] messages, sessionId 状态
  - [x] chatHistory 状态
  - [x] loadDevices, loadTagPoints actions
  - [x] sendMessage, sendMessageStream actions
  - [x] WebSocket 状态管理

### 4.3 组合式函数
- [x] 创建 `frontend/src/composables/modbus/index.ts` - 统一导出
- [x] 创建 `frontend/src/composables/modbus/use-modbus-ws.ts`
- [x] 创建 `frontend/src/composables/modbus/use-funasr-ws.ts`
- [x] 创建 `frontend/src/composables/modbus/use-typewriter.ts` - 打字机效果

---

## Phase 5: 前端页面组件 (P0) ✅ 已完成

> 依赖：Phase 4 完成

### 5.1 设备管理页面
- [x] 创建 `frontend/src/views/module_modbus/device/index.vue`
- [x] 实现设备列表表格
- [x] 实现设备 CRUD 弹窗
- [x] 实现点位管理抽屉

### 5.2 控制页面
- [x] 创建 `frontend/src/views/module_modbus/control/index.vue`
- [x] 实现设备树组件（Element Plus el-tree）
- [x] 实现聊天面板
- [x] 实现消息列表（支持 Markdown 渲染）
- [x] 实现输入框（支持语音按钮）
- [x] 实现快捷指令按钮
- [x] 实现设备详情抽屉

### 5.3 操作日志页面
- [x] 创建 `frontend/src/views/module_modbus/log/index.vue`
- [x] 实现日志列表表格
- [x] 实现日志详情弹窗

---

## Phase 6: 前端高级功能 (P1)

> 依赖：Phase 5 完成

### 6.1 流式对话
- [x] 实现 SSE 客户端逻辑（已在 control.ts 实现）
- [x] 实现打字机效果
- [x] 实现中断生成功能（已实现 abortGeneration）

### 6.2 语音输入
- [x] 实现 AudioWorklet 处理器（已创建 audio-processor.js）
- [x] 实现 FunASR WebSocket 连接（已实现）
- [x] 实现实时识别结果预览（已实现）
- [x] 实现自动静音检测（已实现）

### 6.3 WebSocket 实时通信
- [x] 实现 WebSocket 连接管理（已实现）
- [x] 实现设备状态实时更新（已实现）
- [x] 实现断线重连机制（已实现）

---

## Phase 7: 路由与菜单 (P0) ✅ 已完成

> 依赖：Phase 5 完成

### 7.1 前端路由
- [x] 组件路径已创建：`module_modbus/device/index.vue`
- [x] 组件路径已创建：`module_modbus/control/index.vue`
- [x] 组件路径已创建：`module_modbus/log/index.vue`

### 7.2 菜单配置
- [x] 创建菜单初始化 SQL 脚本 `init_menu.sql`
- [x] 配置一级目录：Modbus控制
- [x] 配置二级菜单：设备管理、AI控制、操作日志
- [x] 配置按钮权限

---

## Phase 8: 权限配置 (P1) ✅ 已完成

> 依赖：Phase 1 完成（数据库迁移）

### 8.1 数据库权限数据
- [x] 添加 modbus 相关权限码（通过 init_menu.sql）
- [x] 关联权限到角色（通过 init_menu.sql）

---

## Phase 9: 测试与文档 (P2)

> 依赖：所有功能模块完成

### 9.1 后端测试
- [x] Schemas 单元测试
- [x] PLC 服务单元测试
- [x] 控制器 API 测试
- [x] 设备 API 测试
- [x] 待确认操作 API 测试
- [x] WebSocket 测试
- [ ] Agent 服务集成测试

### 9.2 文档
- [ ] 更新 CLAUDE.md
- [x] 添加 API 文档

### 9.3 辅助工具
- [x] 创建 `modbus_simulator.py` - Modbus 模拟器（测试用）
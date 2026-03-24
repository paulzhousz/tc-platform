# Modbus 控制模块实施任务清单

## Phase 1: 后端基础设施 (P0)

### 1.1 配置与依赖
- [ ] 在 `backend/app/config/setting.py` 添加 Modbus 配置项
- [ ] 在 `backend/env/.env.dev.example` 添加配置示例
- [ ] 添加依赖：`pymodbus`, `langchain-openai`, `langchain-core`

### 1.2 数据模型
- [ ] 创建 `backend/app/plugin/module_modbus/__init__.py`
- [ ] 创建 `backend/app/plugin/module_modbus/models.py`
  - [ ] DeviceModel
  - [ ] TagPointModel
  - [ ] CommandLogModel
  - [ ] PendingConfirmModel
  - [ ] AgentSessionModel
  - [ ] ChatHistoryModel

### 1.3 数据库迁移
- [ ] 生成 Alembic 迁移脚本
- [ ] 执行数据库迁移

---

## Phase 2: 后端核心服务 (P0)

### 2.1 连接池服务
- [ ] 创建 `control/services/client_factory.py` - Modbus 客户端工厂
- [ ] 创建 `control/services/connection_pool.py` - 连接池管理

### 2.2 PLC 操作服务
- [ ] 创建 `control/services/plc_service.py`
  - [ ] read() - 读取点位
  - [ ] write() - 写入点位
  - [ ] adjust() - 调整参数
  - [ ] search_devices() - 设备搜索
  - [ ] search_tags_in_device() - 点位搜索

### 2.3 LLM Agent 服务
- [ ] 创建 `control/services/agent_service.py`
  - [ ] LangChain 工具定义
  - [ ] chat() - 同步对话
  - [ ] stream_chat() - 流式对话

### 2.4 辅助服务
- [ ] 创建 `control/services/poll_service.py` - 轮询服务
- [ ] 创建 `control/services/websocket_service.py` - WebSocket 服务
- [ ] 创建 `control/services/cleanup_service.py` - 清理服务

---

## Phase 3: 后端 API 路由 (P0)

### 3.1 设备管理模块
- [ ] 创建 `device/` 子模块目录
- [ ] 创建 `device/model.py` - 数据模型导出
- [ ] 创建 `device/schema.py` - Pydantic 验证模型
- [ ] 创建 `device/crud.py` - CRUD 操作
- [ ] 创建 `device/service.py` - 业务逻辑
- [ ] 创建 `device/controller.py` - API 路由

### 3.2 控制操作模块
- [ ] 创建 `control/` 子模块目录
- [ ] 创建 `control/schema.py` - Pydantic 验证模型
- [ ] 创建 `control/controller.py` - API 路由
  - [ ] POST /connect
  - [ ] POST /disconnect
  - [ ] GET /connection-status
  - [ ] POST /chat
  - [ ] POST /chat/stream
  - [ ] POST /read
  - [ ] POST /write
  - [ ] GET /quick-commands

### 3.3 操作日志模块
- [ ] 创建 `log/` 子模块目录
- [ ] 创建 `log/controller.py` - API 路由

### 3.4 待确认操作模块
- [ ] 创建 `pending/` 子模块目录
- [ ] 创建 `pending/controller.py` - API 路由

### 3.5 聊天历史模块
- [ ] 在 `control/controller.py` 中添加聊天历史 API

---

## Phase 4: 配置文件迁移 (P1)

### 4.1 系统提示词
- [ ] 创建 `backend/config/modbus_system_prompt.md`

### 4.2 快捷指令配置
- [ ] 创建 `backend/config/modbus_quick_commands.json`

---

## Phase 5: 前端基础设施 (P0)

### 5.1 API 层
- [ ] 创建 `frontend/src/api/module_modbus/device.ts`
- [ ] 创建 `frontend/src/api/module_modbus/control.ts`
- [ ] 创建 `frontend/src/api/module_modbus/log.ts`
- [ ] 创建 `frontend/src/api/module_modbus/index.ts` - 导出

### 5.2 状态管理
- [ ] 创建 `frontend/src/store/modules/modbus/index.ts`
  - [ ] devices, tagPoints 状态
  - [ ] messages, sessionId 状态
  - [ ] chatHistory 状态
  - [ ] loadDevices, loadTagPoints actions
  - [ ] sendMessage, sendMessageStream actions
  - [ ] WebSocket 状态管理

### 5.3 组合式函数
- [ ] 创建 `frontend/src/composables/modbus/use-modbus-ws.ts`
- [ ] 创建 `frontend/src/composables/modbus/use-funasr-ws.ts`

---

## Phase 6: 前端页面组件 (P0)

### 6.1 设备管理页面
- [ ] 创建 `frontend/src/views/module_modbus/device/index.vue`
- [ ] 实现设备列表表格
- [ ] 实现设备 CRUD 弹窗
- [ ] 实现点位管理抽屉

### 6.2 控制页面
- [ ] 创建 `frontend/src/views/module_modbus/control/index.vue`
- [ ] 实现设备树组件（Element Plus el-tree）
- [ ] 实现聊天面板
- [ ] 实现消息列表（支持 Markdown 渲染）
- [ ] 实现输入框（支持语音按钮）
- [ ] 实现快捷指令按钮
- [ ] 实现设备详情抽屉

### 6.3 操作日志页面
- [ ] 创建 `frontend/src/views/module_modbus/log/index.vue`
- [ ] 实现日志列表表格
- [ ] 实现日志详情弹窗

---

## Phase 7: 前端高级功能 (P1)

### 7.1 流式对话
- [ ] 实现 SSE 客户端逻辑
- [ ] 实现打字机效果
- [ ] 实现中断生成功能

### 7.2 语音输入
- [ ] 实现 AudioWorklet 处理器
- [ ] 实现 FunASR WebSocket 连接
- [ ] 实现实时识别结果预览
- [ ] 实现自动静音检测

### 7.3 WebSocket 实时通信
- [ ] 实现 WebSocket 连接管理
- [ ] 实现设备状态实时更新
- [ ] 实现断线重连机制

---

## Phase 8: 路由与菜单 (P0)

### 8.1 前端路由
- [ ] 添加 `/modbus/device` 路由
- [ ] 添加 `/modbus/control` 路由
- [ ] 添加 `/modbus/log` 路由

### 8.2 菜单配置
- [ ] 添加侧边栏菜单项
- [ ] 配置菜单权限

---

## Phase 9: 权限配置 (P1)

### 9.1 数据库权限数据
- [ ] 添加 modbus 相关权限码
- [ ] 关联权限到角色

---

## Phase 10: 测试与文档 (P2)

### 10.1 后端测试
- [ ] 连接池单元测试
- [ ] PLC 服务单元测试
- [ ] Agent 服务集成测试

### 10.2 文档
- [ ] 更新 CLAUDE.md
- [ ] 添加 API 文档
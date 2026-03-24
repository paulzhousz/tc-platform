# Modbus 控制模块需求规格

## 1. 功能需求清单

### 1.1 设备管理 (FR-DEV)

| ID | 需求 | 优先级 |
|----|------|--------|
| FR-DEV-001 | 设备列表查询（分页、筛选） | P0 |
| FR-DEV-002 | 创建设备（IP、端口、从站ID等） | P0 |
| FR-DEV-003 | 更新设备配置 | P0 |
| FR-DEV-004 | 删除设备（级联删除点位） | P0 |
| FR-TAG-001 | 点位列表查询 | P0 |
| FR-TAG-002 | 创建点位（地址、类型、范围等） | P0 |
| FR-TAG-003 | 更新点位配置 | P0 |
| FR-TAG-004 | 删除点位 | P0 |

### 1.2 设备连接控制 (FR-CONN)

| ID | 需求 | 优先级 |
|----|------|--------|
| FR-CONN-001 | 批量连接设备 | P0 |
| FR-CONN-002 | 断开设备连接 | P0 |
| FR-CONN-003 | 连接状态监控 | P0 |

### 1.3 自然语言控制 (FR-CHAT)

| ID | 需求 | 优先级 |
|----|------|--------|
| FR-CHAT-001 | 自然语言指令解析 | P0 |
| FR-CHAT-002 | 多轮对话上下文 | P0 |
| FR-CHAT-003 | 设备消歧 | P1 |
| FR-CHAT-004 | 点位消歧 | P1 |
| FR-CHAT-005 | 操作确认机制 | P0 |
| FR-CHAT-006 | 流式输出 (SSE) | P0 |

### 1.4 操作日志 (FR-ACTION)

| ID | 需求 | 优先级 |
|----|------|--------|
| FR-ACTION-001 | 结构化执行记录 | P0 |
| FR-ACTION-002 | 日志列表查询 | P1 |
| FR-ACTION-003 | 日志清理服务 | P2 |

### 1.5 待确认操作 (FR-PENDING)

| ID | 需求 | 优先级 |
|----|------|--------|
| FR-PENDING-001 | 待确认列表查询 | P0 |
| FR-PENDING-002 | 确认操作 | P0 |
| FR-PENDING-003 | 拒绝操作 | P0 |

### 1.6 聊天历史 (FR-HIST)

| ID | 需求 | 优先级 |
|----|------|--------|
| FR-HIST-001 | 保存聊天历史 | P1 |
| FR-HIST-002 | 加载聊天历史 | P1 |
| FR-HIST-003 | 删除聊天历史 | P2 |

### 1.7 语音输入 (FR-VOICE)

| ID | 需求 | 优先级 |
|----|------|--------|
| FR-VOICE-001 | 语音输入按钮 | P1 |
| FR-VOICE-002 | FunASR WebSocket 连接 | P1 |
| FR-VOICE-003 | 实时识别结果预览 | P2 |
| FR-VOICE-004 | 自动静音检测 | P2 |

### 1.8 WebSocket 实时通信 (FR-WS)

| ID | 需求 | 优先级 |
|----|------|--------|
| FR-WS-001 | WebSocket 连接 | P1 |
| FR-WS-002 | 实时状态推送 | P1 |

## 2. 权限码定义

| 权限码 | 描述 |
|--------|------|
| modbus:device:view | 查看设备 |
| modbus:device:create | 创建设备 |
| modbus:device:update | 更新设备 |
| modbus:device:delete | 删除设备 |
| modbus:tag:view | 查看点位 |
| modbus:tag:create | 创建点位 |
| modbus:tag:update | 更新点位 |
| modbus:tag:delete | 删除点位 |
| modbus:control:read | 读取控制权限 |
| modbus:control:write | 写入控制权限 |
| modbus:log:view | 查看日志 |
| modbus:pending:view | 查看待确认 |
| modbus:pending:confirm | 确认/拒绝操作 |

## 3. API 端点清单

### 设备管理 API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /modbus/devices | 获取设备列表 |
| POST | /modbus/devices | 创建设备 |
| GET | /modbus/devices/{id} | 获取设备详情 |
| PUT | /modbus/devices/{id} | 更新设备 |
| DELETE | /modbus/devices | 删除设备 |
| GET | /modbus/devices/{id}/tags | 获取设备点位列表 |
| POST | /modbus/devices/{id}/tags | 创建点位 |
| PUT | /modbus/devices/tags/{id} | 更新点位 |
| DELETE | /modbus/devices/tags | 删除点位 |

### 控制操作 API

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /modbus/control/connect | 连接设备 |
| POST | /modbus/control/disconnect | 断开设备 |
| GET | /modbus/control/connection-status | 获取连接状态 |
| POST | /modbus/control/chat | 对话接口 |
| POST | /modbus/control/chat/stream | 流式对话接口 |
| POST | /modbus/control/read | 直接读取 PLC |
| POST | /modbus/control/write | 直接写入 PLC |
| GET | /modbus/control/quick-commands | 获取快捷指令 |

### 日志 API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /modbus/logs | 获取日志列表 |
| GET | /modbus/logs/{id} | 获取日志详情 |

### 待确认 API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /modbus/pending | 获取待确认列表 |
| POST | /modbus/pending/{id}/confirm | 确认操作 |
| POST | /modbus/pending/{id}/reject | 拒绝操作 |

### 聊天历史 API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /modbus/chat-history | 获取历史列表 |
| GET | /modbus/chat-history/{session_id} | 获取历史详情 |
| POST | /modbus/chat-history | 保存历史 |
| DELETE | /modbus/chat-history/{session_id} | 删除历史 |

### WebSocket

| 路径 | 描述 |
|------|------|
| /ws/modbus | WebSocket 连接端点 |
# Modbus 控制模块 API 文档

## 概述

Modbus 控制模块提供 PLC 设备的远程控制、监控和 AI 对话功能。

## 基础路径

```
/api/v1/module_modbus
```

---

## 设备管理 API

### 获取设备列表

**GET** `/device/list`

查询参数:
- `page` (int): 页码，默认 1
- `page_size` (int): 每页数量，默认 10
- `group_name` (str, optional): 设备分组过滤
- `status` (str, optional): 设备状态过滤 (online/offline/error)

响应:
```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": 1,
        "name": "设备名称",
        "code": "DEVICE_001",
        "description": "设备描述",
        "group_name": "分组A",
        "connection_type": "TCP",
        "host": "192.168.1.100",
        "port": 502,
        "slave_id": 1,
        "status": "online",
        "last_seen": "2024-01-01T12:00:00"
      }
    ],
    "total": 100
  }
}
```

### 获取设备详情

**GET** `/device/{id}`

响应:
```json
{
  "code": 200,
  "data": {
    "id": 1,
    "name": "设备名称",
    "code": "DEVICE_001",
    // ... 其他设备属性
  }
}
```

### 创建设备

**POST** `/device`

请求体:
```json
{
  "name": "新设备",
  "code": "DEVICE_002",
  "description": "设备描述",
  "group_name": "分组A",
  "connection_type": "TCP",
  "host": "192.168.1.101",
  "port": 502,
  "slave_id": 1
}
```

### 更新设备

**PUT** `/device/{id}`

请求体: 部分更新的字段

### 删除设备

**DELETE** `/device/{id}`

### 获取设备点位

**GET** `/device/{id}/tags`

响应:
```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": 1,
        "name": "温度",
        "code": "TEMP_001",
        "address": 40001,
        "register_type": "holding",
        "data_type": "FLOAT",
        "unit": "°C",
        "current_value": 25.5,
        "min_value": 0,
        "max_value": 100
      }
    ],
    "total": 10
  }
}
```

### 创建点位

**POST** `/device/{id}/tags`

请求体:
```json
{
  "name": "温度",
  "code": "TEMP_001",
  "address": 40001,
  "register_type": "holding",
  "data_type": "FLOAT",
  "unit": "°C",
  "min_value": 0,
  "max_value": 100,
  "scale_factor": 0.1,
  "offset": 0
}
```

---

## 控制操作 API

### 连接设备

**POST** `/connect`

请求体:
```json
{
  "device_ids": [1, 2, 3]  // 可选，不传则连接所有设备
}
```

响应:
```json
{
  "code": 200,
  "data": {
    "message": "连接成功",
    "results": [
      {"device_id": 1, "success": true},
      {"device_id": 2, "success": false, "error": "连接超时"}
    ]
  }
}
```

### 断开连接

**POST** `/disconnect`

### 获取连接状态

**GET** `/connection-status`

响应:
```json
{
  "code": 200,
  "data": {
    "connected": true,
    "devices": [
      {"id": 1, "name": "设备A", "status": "online"}
    ]
  }
}
```

### AI 对话

**POST** `/chat`

请求体:
```json
{
  "message": "读取设备A的温度值",
  "session_id": "optional-session-id"
}
```

响应:
```json
{
  "code": 200,
  "data": {
    "session_id": "session-uuid",
    "reply": "设备A的温度当前值为 25.5°C",
    "actions": [
      {
        "tool": "read_plc",
        "args": {"device_id": 1, "tag_name": "温度"},
        "status": "success",
        "duration_ms": 150,
        "data": {"value": 25.5, "unit": "°C"}
      }
    ]
  }
}
```

### 流式对话 (SSE)

**POST** `/chat/stream`

请求体: 同 `/chat`

响应格式 (Server-Sent Events):
```
event: token
data: {"content": "设备"}

event: token
data: {"content": "A的"}

event: action
data: {"tool": "read_plc", "status": "running"}

event: action_result
data: {"tool": "read_plc", "status": "success", "data": {"value": 25.5}}

event: done
data: {"session_id": "session-uuid"}
```

### 读取点位

**POST** `/read`

请求体:
```json
{
  "device_id": 1,
  "tag_name": "温度"
}
```

响应:
```json
{
  "code": 200,
  "data": {
    "device_id": 1,
    "tag_name": "温度",
    "value": 25.5,
    "raw_value": 255,
    "unit": "°C"
  }
}
```

### 写入点位

**POST** `/write`

请求体:
```json
{
  "device_id": 1,
  "tag_name": "设定值",
  "value": 50.0
}
```

响应:
```json
{
  "code": 200,
  "data": {
    "device_id": 1,
    "tag_name": "设定值",
    "value": 50.0,
    "unit": "%",
    "success": true,
    "message": "已写入: 50.0 %"
  }
}
```

### 调整参数

**POST** `/adjust`

请求体:
```json
{
  "device_id": 1,
  "tag_name": "设定值",
  "delta": 5.0  // 增量，可以为负数
}
```

### 快捷指令

**GET** `/quick-commands`

响应:
```json
{
  "code": 200,
  "data": [
    {"label": "读取所有温度", "text": "读取所有设备的温度值"},
    {"label": "设备状态", "text": "当前所有设备的状态如何？"}
  ]
}
```

---

## 操作日志 API

### 获取日志列表

**GET** `/logs`

查询参数:
- `page` (int): 页码
- `page_size` (int): 每页数量
- `device_id` (int, optional): 设备过滤
- `action` (str, optional): 操作类型过滤
- `status` (str, optional): 状态过滤
- `start_time` (datetime, optional): 开始时间
- `end_time` (datetime, optional): 结束时间

响应:
```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": 1,
        "user_id": 1,
        "device_id": 1,
        "tag_id": 1,
        "action": "READ",
        "request_value": null,
        "actual_value": 25.5,
        "status": "success",
        "execution_time": 150.5,
        "created_at": "2024-01-01T12:00:00"
      }
    ],
    "total": 100
  }
}
```

### 获取日志详情

**GET** `/logs/{id}`

---

## 待确认操作 API

### 获取待确认列表

**GET** `/pending`

### 确认操作

**POST** `/pending/{id}/confirm`

请求体:
```json
{
  "comment": "确认执行"
}
```

### 拒绝操作

**POST** `/pending/{id}/reject`

请求体:
```json
{
  "comment": "拒绝原因"
}
```

---

## 聊天历史 API

### 获取历史列表

**GET** `/chat-history`

响应:
```json
{
  "code": 200,
  "data": {
    "items": [
      {
        "id": 1,
        "session_id": "session-uuid",
        "title": "设备温度读取",
        "device_count": 2,
        "device_names": ["设备A", "设备B"],
        "start_time": "2024-01-01T10:00:00",
        "end_time": "2024-01-01T11:00:00"
      }
    ],
    "total": 50
  }
}
```

### 获取历史详情

**GET** `/chat-history/{id}`

### 删除历史

**DELETE** `/chat-history/{id}`

---

## WebSocket API

### 连接

**WS** `/ws/modbus?token=<jwt_token>`

### 消息格式

发送消息:
```json
{
  "type": "subscribe",
  "data": {"device_ids": [1, 2]}
}
```

接收消息类型:

#### 设备状态更新
```json
{
  "type": "device_status",
  "data": {
    "device_id": 1,
    "device_name": "设备A",
    "status": "online",
    "last_seen": "2024-01-01T12:00:00"
  }
}
```

#### 点位值更新
```json
{
  "type": "tag_value",
  "data": {
    "device_id": 1,
    "tag_id": 1,
    "tag_name": "温度",
    "value": 26.0,
    "unit": "°C",
    "previous_value": 25.5
  }
}
```

#### 操作结果通知
```json
{
  "type": "operation_result",
  "data": {
    "command_log_id": 100,
    "user_id": 1,
    "success": true,
    "message": "写入成功"
  }
}
```

#### 待确认通知
```json
{
  "type": "pending_confirm",
  "data": {
    "pending_confirm_id": 1,
    "device_name": "设备A",
    "tag_name": "设定值",
    "target_value": 80.0,
    "unit": "%",
    "user_input": "设定温度为80度",
    "ai_explanation": "用户要求设定温度为80度，该操作需要确认",
    "expires_at": "2024-01-01T12:30:00"
  }
}
```

---

## 权限码

| 权限码 | 描述 |
|--------|------|
| `module_modbus:device:query` | 查询设备 |
| `module_modbus:device:create` | 新增设备 |
| `module_modbus:device:detail` | 查看设备详情 |
| `module_modbus:device:update` | 编辑设备 |
| `module_modbus:device:delete` | 删除设备 |
| `module_modbus:tag:query` | 查询点位 |
| `module_modbus:tag:create` | 新增点位 |
| `module_modbus:tag:update` | 编辑点位 |
| `module_modbus:tag:delete` | 删除点位 |
| `module_modbus:control:query` | 查询控制状态 |
| `module_modbus:control:connect` | 连接设备 |
| `module_modbus:control:read` | 读取数据 |
| `module_modbus:control:write` | 写入数据 |
| `module_modbus:log:query` | 查询日志 |
| `module_modbus:log:detail` | 查看日志详情 |

---

## 错误码

| 错误码 | 描述 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
# Modbus 设备控制模块 PRD

**版本**: 1.0
**创建日期**: 2026-03-22
**最后更新**: 2026-03-22

---

## 1. 文档概述

### 1.1 目的

本文档定义 Modbus 设备控制模块的产品需求，包括功能需求、非功能需求、用户场景和验收标准。

### 1.2 范围

设备控制模块提供以下核心能力：
- 自然语言控制 PLC 设备
- 设备与点位管理
- LLM Agent 智能解析与执行
- 实时状态监控与历史记录

**排除范围**：
- 操作日志管理（独立模块）
- 用户权限管理（系统公共模块）

### 1.3 术语定义

| 术语 | 定义 |
|------|------|
| PLC | 可编程逻辑控制器 (Programmable Logic Controller) |
| Modbus | 工业通信协议，支持 TCP 和 RTU 两种模式 |
| 设备 | 连接到系统的 PLC 设备，具有唯一 IP 和端口 |
| 点位 | 设备内的数据地址，如温度传感器、设定值等 |
| 保持寄存器 | 可读写的 16 位寄存器，地址范围 40001-49999 |
| 输入寄存器 | 只读的 16 位寄存器，地址范围 30001-39999 |
| 线圈 | 可读写的布尔值，地址范围 1-9999 |
| 离散输入 | 只读的布尔值，地址范围 1-9999 |

---

## 2. 用户角色

| 角色 | 描述 | 主要场景 |
|------|------|----------|
| 操作员 | 日常设备操作人员 | 通过自然语言控制设备、查看状态 |
| 工程师 | 设备配置和维护人员 | 配置设备和点位参数、调试系统 |
| 管理员 | 系统管理人员 | 管理用户权限、查看审计日志 |

---

## 3. 功能需求

### 3.1 设备管理

#### FR-DEV-001: 设备列表查询

**描述**: 查看系统中配置的所有设备

**用户故事**: 作为工程师，我需要查看设备列表，了解当前系统连接了哪些设备

**验收标准**:
- GIVEN 系统中存在设备数据
- WHEN 用户访问设备管理页面
- THEN 显示设备列表，包含名称、编码、分组、连接状态
- AND 支持按分组、状态筛选
- AND 显示设备在线/离线状态

#### FR-DEV-002: 创建设备

**描述**: 添加新的 PLC 设备到系统

**验收标准**:
- GIVEN 用户具有设备创建权限
- WHEN 用户填写设备信息（名称、编码、IP、端口、从站ID等）
- AND 提交创建请求
- THEN 系统创建设备记录
- AND 自动尝试连接设备
- AND 返回连接结果

**字段约束**:
| 字段 | 类型 | 必填 | 约束 |
|------|------|------|------|
| name | string | 是 | 最大100字符 |
| code | string | 是 | 最大50字符，唯一 |
| host | string | 是 | 有效IP地址 |
| port | int | 否 | 默认502，范围1-65535 |
| slave_id | int | 否 | 默认1，≥1 |
| connection_type | enum | 否 | TCP 或 RTU_OVER_TCP |

#### FR-DEV-003: 更新设备

**描述**: 修改设备配置信息

**验收标准**:
- GIVEN 设备存在
- WHEN 用户修改设备信息并提交
- THEN 系统更新设备记录
- AND 重置设备连接（断开旧连接，尝试新连接）

#### FR-DEV-004: 删除设备

**描述**: 从系统中移除设备

**验收标准**:
- GIVEN 设备存在
- WHEN 用户确认删除
- THEN 系统断开设备连接
- AND 删除设备记录
- AND 级联删除关联的点位数据

---

### 3.2 点位管理

#### FR-TAG-001: 点位列表查询

**描述**: 查看设备下的所有点位配置

**验收标准**:
- GIVEN 设备存在且有点位数据
- WHEN 用户选择设备查看点位
- THEN 显示点位列表，支持分页
- AND 支持按名称、寄存器类型筛选
- AND 显示点位当前值（如已连接）

#### FR-TAG-002: 创建点位

**描述**: 为设备添加新的数据点位

**验收标准**:
- GIVEN 设备存在
- WHEN 用户填写点位信息
- AND 提交创建请求
- THEN 系统创建点位记录

**关键字段**:
| 字段 | 描述 | 约束 |
|------|------|------|
| address | Modbus地址 | ≥0，支持PLC编程地址自动转换 |
| register_type | 寄存器类型 | holding, input, coil, discrete |
| data_type | 数据类型 | INT16, UINT16, INT32, FLOAT, BOOL |
| scale_factor | 缩放因子 | 工程值 = 原始值 × scale_factor + offset |
| aliases | 语义别名 | JSON数组，用于AI语义匹配 |
| requires_confirmation | 是否需确认 | 布尔值 |
| confirmation_threshold | 确认阈值 | 百分比值，超过该比例的值需确认 |

#### FR-TAG-003: 点位值范围校验

**描述**: 写入时自动校验值是否在安全范围内

**验收标准**:
- GIVEN 点位配置了 min_value 和 max_value
- WHEN 用户尝试写入值
- THEN 系统校验值是否在范围内
- IF 超出范围，THEN 返回错误信息
- IF 在范围内，THEN 继续执行写入

---

### 3.3 设备连接控制

#### FR-CONN-001: 批量连接设备

**描述**: 一键连接所有或指定设备

**验收标准**:
- GIVEN 用户具有控制权限
- WHEN 用户点击"连接设备"按钮
- THEN 系统尝试建立 Modbus TCP 连接
- AND 为每个设备创建连接池
- AND 更新设备在线状态
- AND 显示连接结果摘要

**连接池配置**:
- 每设备最大连接数: 可配置（默认5）
- 连接超时: 可配置（默认5秒）
- 读写超时: 可配置（默认10秒）

#### FR-CONN-002: 断开设备连接

**描述**: 断开指定或所有设备连接

**验收标准**:
- GIVEN 设备已连接
- WHEN 用户请求断开
- THEN 系统关闭连接池
- AND 更新设备状态为离线
- AND 停止轮询服务（如断开全部）

#### FR-CONN-003: 连接状态监控

**描述**: 实时查看设备连接健康状态

**验收标准**:
- GIVEN 设备已连接
- WHEN 用户查看连接状态
- THEN 显示可用连接数/最大连接数
- AND 显示设备在线状态
- AND 支持健康检查

---

### 3.4 自然语言控制（核心功能）

#### FR-CHAT-001: 自然语言指令解析

**描述**: 用户通过自然语言控制设备

**用户故事**: 作为操作员，我需要用日常语言控制设备，无需记忆复杂的命令格式

**支持的指令类型**:

| 操作类型 | 示例指令 | 映射工具 |
|---------|---------|---------|
| 查询 | "空调温度是多少" | read_plc |
| 设定 | "把空调温度设为26度" | write_plc |
| 调高 | "温度调高5度" | adjust_plc |
| 调低 | "降低频率10Hz" | adjust_plc |

**验收标准**:
- GIVEN 设备已连接
- WHEN 用户输入自然语言指令
- THEN LLM Agent 解析用户意图
- AND 识别目标设备、点位和操作
- AND 执行对应操作
- AND 返回执行结果

#### FR-CHAT-002: 多轮对话上下文

**描述**: 保持对话上下文，支持代词引用

**验收标准**:
- GIVEN 用户之前操作过设备
- WHEN 用户说"把它调高5度"
- THEN 系统识别"它"指代上次操作的设备/点位
- AND 基于上次操作的上下文执行调整

**上下文保持规则**:
- last_device: 最近操作的设备
- last_tag: 最近操作的点位
- last_operation: 最近的操作类型和值
- 会话TTL: 可配置（默认10分钟）

#### FR-CHAT-003: 设备消歧

**描述**: 当指令匹配多个设备时，引导用户选择

**验收标准**:
- GIVEN 用户指令匹配多个设备
- AND 分差 ≤ 20（消歧阈值）
- WHEN LLM 检测到歧义
- THEN 返回消歧选项列表
- AND 等待用户选择
- IF 用户选择编号，THEN 使用对应设备继续

**示例**:
```
用户: 查看空调温度
AI: 检测到多个设备匹配，请选择：
    1. 测试空调
    2. 智能空调
用户: 2
AI: 智能空调当前温度为 26°C
```

#### FR-CHAT-004: 点位消歧

**描述**: 当指令匹配多个点位时，引导用户选择

**验收标准**:
- 同 FR-CHAT-003，但针对点位

#### FR-CHAT-005: 操作确认机制

**描述**: 高风险操作需要人工确认

**触发条件**:
1. 点位配置了 `requires_confirmation = true`
2. 写入值超过 `confirmation_threshold` 阈值

**验收标准**:
- GIVEN 操作触发确认条件
- WHEN LLM 准备执行写入
- THEN 返回确认请求
- AND 显示操作详情（设备、点位、目标值）
- AND 等待用户确认或取消
- IF 用户确认，THEN 执行操作
- IF 用户取消，THEN 放弃操作

#### FR-CHAT-006: 流式输出

**描述**: 实时显示 AI 生成内容

**验收标准**:
- GIVEN 用户发送消息
- WHEN LLM 生成回复
- THEN 通过 SSE 实时推送 token
- AND 显示工具调用过程
- AND 支持中断生成

---

### 3.5 ActionStep 执行记录

#### FR-ACTION-001: 结构化执行记录

**描述**: 记录每次工具调用的完整信息

**验收标准**:
- GIVEN 工具执行
- WHEN 执行完成
- THEN 记录以下信息：
  - 工具名称 (tool)
  - 调用参数 (args)
  - 执行状态 (status)
  - 开始/结束时间 (started_at, finished_at)
  - 执行耗时 (duration_ms)
  - 结构化结果 (data)
  - 错误信息 (error, 如失败)
  - 操作日志ID (command_log_id)

#### FR-ACTION-002: 工具输出结构化

**描述**: 各工具返回结构化数据而非简单字符串

**read_plc 返回数据**:
| 字段 | 类型 | 描述 |
|------|------|------|
| device_id | int | 设备ID |
| device_name | string | 设备名称 |
| tag_id | int | 点位ID |
| tag_name | string | 点位名称 |
| value | float | 当前值 |
| unit | string | 单位 |
| min_value | float | 最小值 |
| max_value | float | 最大值 |

**write_plc 返回数据**:
| 字段 | 类型 | 描述 |
|------|------|------|
| device_id | int | 设备ID |
| device_name | string | 设备名称 |
| tag_id | int | 点位ID |
| tag_name | string | 点位名称 |
| request_value | float | 请求写入值 |
| actual_value | float | 实际写入值 |
| unit | string | 单位 |

**adjust_plc 返回数据**:
| 字段 | 类型 | 描述 |
|------|------|------|
| device_id | int | 设备ID |
| device_name | string | 设备名称 |
| tag_id | int | 点位ID |
| tag_name | string | 点位名称 |
| previous_value | float | 调整前值 |
| delta | float | 变化量 |
| new_value | float | 新值 |
| unit | string | 单位 |

---

### 3.6 快捷指令

#### FR-QUICK-001: 快捷指令配置

**描述**: 预定义常用操作，一键执行

**验收标准**:
- GIVEN 快捷指令配置文件存在
- WHEN 用户进入控制页面
- THEN 显示快捷指令按钮
- AND 按钮文案根据用户语言设置显示（中/英文）

**配置示例**:
```json
{
  "quick_commands": [
    {
      "id": "view_status",
      "label": { "zh": "查看状态", "en": "View Status" },
      "text": { "zh": "查看所有设备状态", "en": "View all device status" }
    }
  ]
}
```

#### FR-QUICK-002: 快捷指令执行

**描述**: 点击快捷指令按钮发送预设指令

**验收标准**:
- WHEN 用户点击快捷指令按钮
- THEN 自动发送预设指令文本
- AND 触发对话流程

---

### 3.7 语音输入集成

#### FR-VOICE-001: 语音输入按钮

**描述**: 支持语音方式输入指令

**验收标准**:
- GIVEN 用户进入控制页面
- THEN 输入框旁显示语音输入按钮
- WHEN 用户点击语音按钮
- THEN 开始录音
- AND 显示录音状态动画（麦克风图标变为停止图标）

#### FR-VOICE-002: 实时识别结果预览

**描述**: 录音过程中显示实时识别结果

**验收标准**:
- GIVEN 用户正在录音
- WHEN FunASR 返回实时识别结果
- THEN 输入框上方显示实时识别文本
- AND 文本随识别进度实时更新

#### FR-VOICE-003: 语音识别结果处理

**描述**: 将语音识别结果填入输入框

**验收标准**:
- GIVEN 用户完成语音输入
- WHEN 语音识别完成（收到 is_final 信号）
- THEN 识别结果填入输入框
- AND 用户可编辑或直接发送

#### FR-VOICE-004: 自动静音检测

**描述**: 检测用户停止说话后自动结束录音

**验收标准**:
- GIVEN 用户正在录音
- WHEN 检测到持续静音超过 1.5 秒
- THEN 自动停止录音
- AND 发送结束信号给 FunASR 服务

**静音检测参数**:
| 参数 | 默认值 | 描述 |
|------|--------|------|
| silenceThreshold | 0.01 | RMS 音量阈值 |
| silenceDuration | 1.5s | 静音持续时间 |

#### FR-VOICE-005: FunASR 服务连接

**描述**: 连接 FunASR Docker 服务进行语音识别

**验收标准**:
- GIVEN FunASR 服务已启动
- WHEN 用户开始录音
- THEN 建立 WebSocket 连接
- AND 发送初始化消息（2pass-offline 模式）
- AND 发送音频数据流

**服务配置**:
| 参数 | 值 | 描述 |
|------|-----|------|
| 服务地址 | ws://localhost:10095 | Docker 服务地址 |
| 采样率 | 16000 Hz | 音频采样率 |
| 模式 | 2pass-offline | 实时流式 + 离线修正 |
| 音频格式 | PCM Int16 | 原始音频格式 |

#### FR-VOICE-006: 语音输入错误处理

**描述**: 处理语音输入过程中的各种错误

**验收标准**:
- GIVEN 用户尝试语音输入
- WHEN 麦克风权限被拒绝
- THEN 显示权限请求提示
- WHEN FunASR 服务不可用
- THEN 显示"语音服务不可用"错误
- WHEN 识别过程出错
- THEN 显示错误信息并允许重试

---

### 3.8 聊天历史

#### FR-HIST-001: 保存聊天历史

**描述**: 将当前对话保存到数据库

**验收标准**:
- GIVEN 当前对话有消息
- WHEN 用户触发保存（新建对话时自动保存）
- THEN 保存到数据库
- AND 生成标题（首条用户消息摘要）

#### FR-HIST-002: 加载聊天历史

**描述**: 加载历史对话记录

**验收标准**:
- GIVEN 用户有历史对话
- WHEN 用户点击历史记录
- THEN 显示聊天历史列表
- AND 显示会话标题、时间、设备数量
- AND 支持点击加载详情

#### FR-HIST-003: 删除聊天历史

**描述**: 删除指定或全部历史记录

**验收标准**:
- GIVEN 历史记录存在
- WHEN 用户确认删除
- THEN 删除记录并刷新列表

---

### 3.9 WebSocket 实时通信

#### FR-WS-001: WebSocket 连接

**描述**: 建立实时通信连接

**验收标准**:
- GIVEN 用户已登录
- WHEN 用户连接设备
- THEN 建立 WebSocket 连接
- AND 发送心跳保持连接
- AND 支持断线重连（最多5次）

#### FR-WS-002: 实时状态推送

**描述**: 实时接收设备状态变化

**验收标准**:
- GIVEN WebSocket 已连接
- WHEN 设备状态变化
- THEN 推送状态更新消息
- AND 前端实时更新UI

---

## 4. 非功能需求

### 4.1 性能需求

| ID | 需求描述 | 指标 |
|----|---------|------|
| NFR-PERF-001 | 设备列表加载时间 | < 1秒 |
| NFR-PERF-002 | 单次读写操作响应时间 | < 500ms |
| NFR-PERF-003 | LLM 对话首字响应时间 | < 3秒 |
| NFR-PERF-004 | 连接池单设备最大连接数 | 可配置，默认5 |
| NFR-PERF-005 | 支持并发连接设备数 | ≥ 10 |

### 4.2 可用性需求

| ID | 需求描述 |
|----|---------|
| NFR-AVAIL-001 | 连接断开后自动重连 |
| NFR-AVAIL-002 | 连接池提供健康检查接口 |
| NFR-AVAIL-003 | LLM 服务不可用时返回友好错误信息 |

### 4.3 安全需求

| ID | 需求描述 |
|----|---------|
| NFR-SEC-001 | 所有 API 需要权限验证 |
| NFR-SEC-002 | 写入操作记录审计日志 |
| NFR-SEC-003 | 敏感操作需二次确认 |
| NFR-SEC-004 | 值范围校验防止危险写入 |
| NFR-SEC-005 | WebSocket 使用 Token 认证 |

### 4.4 可维护性需求

| ID | 需求描述 |
|----|---------|
| NFR-MAINT-001 | 系统提示词支持外部文件配置 |
| NFR-MAINT-002 | 快捷指令支持热更新配置 |
| NFR-MAINT-003 | 连接参数支持环境变量配置 |

---

## 5. 配置参数

### 5.1 Modbus 配置

| 参数名 | 默认值 | 描述 |
|--------|--------|------|
| MODBUS_POOL_SIZE | 5 | 每设备连接池大小 |
| MODBUS_CONNECT_TIMEOUT | 5 | 连接超时（秒） |
| MODBUS_READ_TIMEOUT | 10 | 读写超时（秒） |
| MODBUS_POLL_ENABLED | true | 是否启用轮询 |
| MODBUS_LOG_RETENTION_DAYS | 30 | 日志保留天数 |
| MODBUS_PENDING_EXPIRE_MINUTES | 10 | 待确认记录过期时间 |

### 5.2 LLM 配置

| 参数名 | 默认值 | 描述 |
|--------|--------|------|
| LLM_BASE_URL | - | LLM API 地址 |
| LLM_API_KEY | - | LLM API 密钥 |
| LLM_MODEL | gpt-4o-mini | 模型名称 |
| LLM_SESSION_TTL_MINUTES | 10 | Agent 会话 TTL |

### 5.3 FunASR 语音服务配置

| 参数名 | 默认值 | 描述 |
|--------|--------|------|
| FUNASR_WS_URL | ws://localhost:10095 | FunASR WebSocket 地址 |
| FUNASR_MODE | 2pass-offline | 识别模式 |
| FUNASR_AUDIO_FS | 16000 | 音频采样率 |
| SILENCE_THRESHOLD | 0.01 | 静音检测阈值 |
| SILENCE_DURATION | 1.5 | 静音持续时间（秒） |

---

## 6. API 清单

### 设备管理 API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /modbus/devices | 获取设备列表 |
| POST | /modbus/devices | 创建设备 |
| GET | /modbus/devices/{id} | 获取设备详情 |
| PUT | /modbus/devices/{id} | 更新设备 |
| DELETE | /modbus/devices/{id} | 删除设备 |
| GET | /modbus/devices/{id}/tags | 获取设备点位列表 |
| POST | /modbus/devices/{id}/tags | 创建点位 |
| PUT | /modbus/devices/tags/{id} | 更新点位 |
| DELETE | /modbus/devices/tags/{id} | 删除点位 |

### 控制操作 API

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /modbus/control/connect | 连接设备 |
| POST | /modbus/control/disconnect | 断开设备 |
| GET | /modbus/control/connection-status | 获取连接状态 |
| POST | /modbus/control/chat | 对话接口 |
| POST | /modbus/control/chat/stream | 流式对话接口 |
| POST | /modbus/control/read | 直接读取PLC |
| POST | /modbus/control/write | 直接写入PLC |
| GET | /modbus/control/quick-commands | 获取快捷指令 |

### 聊天历史 API

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /modbus/control/chat-history | 获取历史列表 |
| GET | /modbus/control/chat-history/{session_id} | 获取历史详情 |
| POST | /modbus/control/chat-history | 保存历史 |
| DELETE | /modbus/control/chat-history/{session_id} | 删除历史 |
| DELETE | /modbus/control/chat-history | 清空历史 |

---

## 7. 权限码定义

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

---

## 8. 验收测试场景

### 场景 1: 完整控制流程

1. 用户登录系统
2. 进入设备控制页面
3. 点击"连接设备"
4. 输入"空调温度是多少"
5. 系统返回当前温度值
6. 输入"把温度调高2度"
7. 系统执行调整并返回结果
8. 点击"断开设备"

### 场景 2: 操作确认流程

1. 用户输入"设置频率为50Hz"
2. 系统检测到该点位需要确认
3. 返回确认请求
4. 用户选择"确认执行"
5. 系统执行操作
6. 返回成功结果

### 场景 3: 多设备消歧

1. 系统中有两个空调设备
2. 用户输入"空调温度"
3. 系统返回消歧选项
4. 用户选择"2"
5. 系统返回智能空调的温度

---

## 9. 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0 | 2026-03-22 | 初始版本 |
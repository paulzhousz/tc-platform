# Proposal: Modbus Agent 超时配置与 UI 显示修复

## Why

PLC 控制智能代理在长时间运行场景下存在两个关键问题：

1. **缺少超时保护**：LLM API 调用和流式响应没有超时控制，在网络波动或模型响应慢时会导致前端无限等待，影响用户体验和系统稳定性。

2. **推理过程显示不完整**：消歧流程中 `action_start` 事件未正确发送，导致前端推理步骤状态显示为空，用户无法看到 Agent 正在执行的操作。

这两个问题直接影响生产环境的可用性和用户对 AI Agent 行为的可观测性，需要尽快修复。

## What Changes

### 新增功能

- **LLM 超时配置机制**：新增 3 个可配置的超时参数
  - `modbus_llm_request_timeout`：LLM API 请求超时（默认 60s）
  - `modbus_llm_stream_timeout`：流式响应整体超时（默认 120s）
  - `modbus_tool_execution_timeout`：工具执行超时（默认 30s）

- **流式超时检查**：在 `stream_chat` 方法中实现 elapsed time 检查，超过阈值时发送错误事件并终止流

### Bug 修复

- **推理步骤显示修复**：在 model updates 分支补充 `action_start` 事件发送，确保消歧流程中前端能正确显示工具调用状态和参数

- **响应消息清理**：移除确认/消歧响应中泄露的内部指令，更新系统提示词匹配新的 JSON 响应格式

### 改进

- **工具调用参数跟踪**：使用 `pending_tool_calls` 字典统一管理工具调用状态，解决 `action_end` 事件中参数为空的问题

## Capabilities

### New Capabilities

- `llm-timeout-config`: LLM 调用超时配置能力，包括请求超时、流式超时和工具执行超时的配置管理

### Modified Capabilities

- `modbus/requirements`: 新增超时配置相关需求项（FR-CHAT-007: LLM 超时控制）

## Impact

### 后端影响

| 文件 | 影响 |
|------|------|
| `control/services/agent_service.py` | 添加超时检查逻辑，修复 action_start 事件发送 |
| `control/services/config_service.py` | 新增超时配置项和类型转换 |
| `config/modbus_system_prompt.md` | 更新响应格式说明 |
| `init/init_params.sql` | 新增超时配置数据库初始化 |

### 前端影响

| 文件 | 影响 |
|------|------|
| `views/module_modbus/control/index.vue` | 新增 step-method-name 显示样式 |
| `store/modules/modbus.store.ts` | 无变更（action_start 事件处理已存在） |

### API 影响

- 无新增 API，现有 `/modbus/control/chat/stream` 接口行为变化：
  - 新增 `error` 类型事件（超时错误）
  - `action_start` 事件在消歧流程中正常发送

### 数据库影响

- 新增 3 条 `sys_param` 配置项记录

### 配置影响

- 需执行 `init_params.sql` 或手动添加配置项到数据库
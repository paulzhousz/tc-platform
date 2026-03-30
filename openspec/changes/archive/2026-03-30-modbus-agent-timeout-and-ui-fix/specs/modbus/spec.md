# Modbus 控制模块需求规格增量

> 变更: modbus-agent-timeout-and-ui-fix
> 基线: openspec/specs/modbus/requirements.md

## ADDED Requirements

### Requirement: FR-CHAT-007 LLM Timeout Control

系统 SHALL 为 AI Agent 的 LLM 调用提供超时保护机制，防止请求无限等待影响用户体验。

配置项：
| 配置键 | 描述 | 默认值 |
|--------|------|--------|
| modbus_llm_request_timeout | LLM API 请求超时 | 60s |
| modbus_llm_stream_timeout | 流式响应整体超时 | 120s |
| modbus_tool_execution_timeout | 工具执行超时 | 30s |

#### Scenario: Request Timeout Triggers Error

- **WHEN** LLM API 请求超过配置的 request_timeout 时间
- **THEN** 系统抛出超时异常并返回错误响应给前端

#### Scenario: Stream Timeout Triggers SSE Error Event

- **WHEN** 流式响应超过配置的 stream_timeout 时间
- **THEN** 系统发送 `{"type": "error", "error": "响应超时，请稍后重试"}` SSE 事件
- **AND** 终止流式迭代

---

### Requirement: FR-CHAT-008 Action Start Event in Disambiguation

系统 SHALL 在消歧流程中正确发送 action_start 事件，确保前端能显示推理步骤状态。

#### Scenario: Action Start from Tool Call Chunks

- **WHEN** LangChain Agent 发送 AIMessageChunk 包含 tool_call_chunks
- **THEN** 系统提取工具名称和参数
- **AND** 发送 `{"type": "action_start", "action": {"tool": <name>, "args": <args>, "status": "running"}}` SSE 事件

#### Scenario: Action Start from Model Updates

- **WHEN** LangGraph 在 updates 分支返回 model 更新包含 tool_calls
- **THEN** 系统检查 tool_call_id 是否已在 pending_tool_calls 中
- **AND** 若未记录则发送 action_start 事件
- **AND** 记录到 pending_tool_calls 字典供后续 action_end 使用

#### Scenario: Action End Contains Correct Args

- **WHEN** 工具执行完成返回 ToolMessage
- **THEN** 系统从 pending_tool_calls 获取记录的 args 参数
- **AND** 发送 `{"type": "action_end", "action": {"tool": <name>, "args": <args>, "result": <result>, "status": <status>}}` SSE 事件
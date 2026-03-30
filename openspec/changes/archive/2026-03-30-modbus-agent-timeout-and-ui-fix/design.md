# Design: Modbus Agent 超时配置与 UI 显示修复

> 变更: modbus-agent-timeout-and-ui-fix

## Context

### 背景

PLC 控制智能代理（AgentService）使用 LangChain 1.x 和 LangGraph 实现，通过 SSE 流式响应与前端通信。当前存在两个关键问题：

1. **超时保护缺失**：ChatOpenAI 实例未配置 request_timeout，stream_chat 方法未实现整体超时检查
2. **事件发送不完整**：LangGraph 的 updates 分支中 model 更新包含完整 tool_calls，但未发送 action_start 事件

### 当前状态

```
agent_service.py:
├── create_agent_graph() → ChatOpenAI 无 request_timeout
├── stream_chat() → 无 elapsed time 检查
│   ├── messages 分支 → tool_call_chunks → 发送 action_start ✓
│   └── updates 分支:
│       ├── tools → ToolMessage → 发送 action_end (args 为空) ❌
│       └── model → AIMessage.tool_calls → 未发送 action_start ❌
└── pending_tool_calls → 仅在 messages 分支填充
```

### 约束

- 遵循现有 SSE 事件格式规范
- 配置项使用 ModbusConfigService 管理
- 不改变现有 API 接口签名

## Goals / Non-Goals

**Goals:**
- 为 LLM 调用添加三层超时保护（request/stream/tool）
- 修复消歧流程中 action_start 事件缺失问题
- 确保 action_end 事件包含完整 args 参数
- 清理用户可见响应中的内部指令泄露

**Non-Goals:**
- 不实现 modbus_tool_execution_timeout 的实际应用（仅配置）
- 不改变前端组件结构
- 不添加新的 API 端点

## Decisions

### D1: 使用 elapsed time 检查而非 asyncio.timeout()

**选择**: 在 `async for` 循环内检查 elapsed time

**原因**:
- `asyncio.timeout()` 对 generator/async iterator 不友好，需要包装整个迭代
- elapsed time 检查在每次迭代开始时执行，更精准控制
- 可在超时时发送友好的错误事件给前端

**替代方案**:
- 使用 `asyncio.timeout()` 包装整个 astream 调用
  - 缺点：超时时无法发送 SSE 事件，前端只能收到连接断开
- 使用信号量或外部监控
  - 缺点：实现复杂，增加维护成本

### D2: pending_tool_calls 字典统一管理

**选择**: 使用字典 `pending_tool_calls: dict[str, dict]` 跟踪工具调用

**原因**:
- tool_call_chunks 和 model updates 两个分支都会产生 tool_calls
- action_end 事件需要 args 参数，但 ToolMessage 不包含原始参数
- 字典可跨分支共享，确保参数一致性

**结构**:
```python
pending_tool_calls[tool_call_id] = {
    "name": str,
    "args": dict,
    "started_at": str,  # ISO format
}
```

### D3: model updates 分支补充 action_start

**选择**: 在 model updates 分支检查并发送 action_start

**原因**:
- 消歧流程中 LangGraph 可能直接返回完整 AIMessage（非 chunk）
- messages 分支的 tool_call_chunks 可能为空或不完整
- 两个分支互补，确保前端始终收到 action_start 事件

**实现要点**:
- 检查 `tool_call_id not in pending_tool_calls` 防止重复发送
- 使用相同的 action_start 格式

## Risks / Trade-offs

### R1: 超时时间配置可能不适用于所有场景

**风险**: 60s/120s 默认值可能对复杂查询不足

**缓解**:
- 配置项可通过管理后台调整
- 提供合理的默认值并记录调整建议

### R2: pending_tool_calls 内存泄漏

**风险**: 字典在异常中断时可能未清理

**缓解**:
- 字典在方法内定义，随方法结束自动释放
- 无跨请求共享风险

### R3: 两个分支同时发送 action_start

**风险**: messages 和 updates 分支可能对同一工具发送两次

**缓解**:
- 检查 `tool_call_id not in pending_tool_calls` 条件
- 第二次发送时跳过

## Migration Plan

### 步骤

1. **部署数据库配置**
   ```sql
   -- 执行 init_params.sql 新增配置项
   docker exec -i postgres psql -U root -d tc-platform < backend/app/plugin/module_modbus/init/init_params.sql
   ```

2. **重启后端服务**
   - AgentService 加载新配置
   - 验证超时参数生效

3. **前端无需变更**
   - action_start 事件处理已存在
   - step-method-name 样式已添加

### 回滚策略

- 删除 sys_param 中 3 条超时配置
- 代码回退到上一 commit
- 前端无变更无需回滚

## Open Questions

- [已解决] `modbus_tool_execution_timeout` 是否需要应用到 read_plc/write_plc？
  - 当前仅配置，不实现应用
  - PLC 通信已有 `MODBUS_READ_TIMEOUT` 在 connection_pool.py
  - 可能重复，后续考虑统一
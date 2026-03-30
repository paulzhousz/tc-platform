# LLM Timeout 配置规格

> 变更: modbus-agent-timeout-and-ui-fix

## ADDED Requirements

### Requirement: LLM Request Timeout

系统 SHALL 为 LLM API 请求提供可配置的超时参数，防止请求无限等待。

配置参数：
- `modbus_llm_request_timeout`：LLM API 请求超时时间（秒），默认 60

#### Scenario: 配置读取

- **WHEN** AgentService 初始化 ChatOpenAI 实例
- **THEN** 系统从配置服务读取 `modbus_llm_request_timeout` 参数值
- **AND** 设置 ChatOpenAI 的 `request_timeout` 参数

#### Scenario: 默认值生效

- **WHEN** 配置服务中未定义 `modbus_llm_request_timeout`
- **THEN** 系统使用默认值 60 秒

#### Scenario: 超时触发

- **WHEN** LLM API 请求超过配置的超时时间
- **THEN** ChatOpenAI 抛出超时异常
- **AND** AgentService 捕获异常并返回错误响应

---

### Requirement: LLM Stream Timeout

系统 SHALL 为流式响应提供整体超时控制，防止长时间无响应。

配置参数：
- `modbus_llm_stream_timeout`：流式响应整体超时时间（秒），默认 120

#### Scenario: 流式超时检查

- **WHEN** AgentService 执行 stream_chat 方法
- **THEN** 系统在每次迭代开始时检查 elapsed time
- **AND** 当 elapsed > stream_timeout 时发送 error 事件并终止流

#### Scenario: 超时错误事件

- **WHEN** 流式响应超过配置的超时时间
- **THEN** 系统发送 SSE 事件：`{"type": "error", "error": "响应超时，请稍后重试"}`
- **AND** 终止流式迭代并结束响应

---

### Requirement: Tool Execution Timeout

系统 SHALL 为 PLC 工具执行提供可配置的超时参数。

配置参数：
- `modbus_tool_execution_timeout`：工具执行超时时间（秒），默认 30

#### Scenario: 配置存储

- **WHEN** 系统初始化模块参数
- **THEN** 将 `modbus_tool_execution_timeout` 配置项写入 sys_param 表

#### Scenario: 配置类型转换

- **WHEN** ModbusConfigService 加载配置
- **THEN** 将 `modbus_tool_execution_timeout` 从字符串转换为整数类型
- **AND** 纳入 INT_KEYS 类型转换列表

---

### Requirement: Timeout Configuration Persistence

系统 SHALL 将超时配置持久化到数据库。

#### Scenario: 数据库初始化

- **WHEN** 执行 init_params.sql
- **THEN** 创建以下 sys_param 记录：
  - `modbus_llm_request_timeout` (60s)
  - `modbus_llm_stream_timeout` (120s)
  - `modbus_tool_execution_timeout` (30s)

#### Scenario: 配置热加载

- **WHEN** 系统运行时
- **THEN** 配置服务从 Redis 缓存读取超时参数
- **AND** AgentService 动态使用当前配置值
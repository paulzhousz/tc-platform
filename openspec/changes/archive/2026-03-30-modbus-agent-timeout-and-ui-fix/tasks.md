# Tasks: Modbus Agent 超时配置与 UI 显示修复

> 变更: modbus-agent-timeout-and-ui-fix

## 1. 数据库配置层

- [x] 1.1 添加超时配置项到 init_params.sql
  - `modbus_llm_request_timeout` (60s)
  - `modbus_llm_stream_timeout` (120s)
  - `modbus_tool_execution_timeout` (30s)

- [x] 1.2 更新 config_service.py DEFAULTS 字典
  - 添加 3 个超时配置默认值

- [x] 1.3 更新 config_service.py INT_KEYS 类型转换
  - 添加 3 个超时配置到整数类型转换列表

## 2. Agent 服务层 - 超时配置

- [x] 2.1 添加 request_timeout 到 ChatOpenAI 实例
  - 在 create_agent_graph() 中设置 `request_timeout=self._config.get("modbus_llm_request_timeout", 60)`

- [x] 2.2 实现 stream_chat 流式超时检查
  - 添加 elapsed time 检查逻辑
  - 超时时发送 error SSE 事件

## 3. Agent 服务层 - 事件修复

- [x] 3.1 添加 pending_tool_calls 字典管理工具调用参数
  - 在 messages 分支记录 tool_call_chunks
  - 在 updates 分支记录 model tool_calls

- [x] 3.2 在 model updates 分支发送 action_start 事件
  - 检查 tool_call_id 是否已在 pending_tool_calls
  - 若未记录则发送 action_start 并记录参数

- [x] 3.3 修复 action_end 事件参数来源
  - 从 pending_tool_calls 获取 args 参数
  - 发送完整的 action_end SSE 事件

## 4. 系统提示词更新

- [x] 4.1 清理确认/消歧响应中的内部指令泄露
  - 修改 write_plc、adjust_plc 确认响应格式
  - 修改 search_device、search_tag_mapping 消歧响应格式

- [x] 4.2 更新 modbus_system_prompt.md
  - 简化响应格式说明
  - 移除冗余的消歧格式和反馈格式章节

## 5. 前端样式更新

- [x] 5.1 添加 step-method-name CSS 样式
  - 显示工具方法名样式

- [x] 5.2 添加 Raw Tool Method Name 显示
  - 在推理步骤中显示 step.tool 字段

## 6. 验证与测试

- [ ] 6.1 执行 init_params.sql 初始化数据库配置
  - 运行 SQL 文件添加 sys_param 记录

- [ ] 6.2 验证超时配置生效
  - 测试 request_timeout 正常工作
  - 测试 stream_timeout 超时事件发送

- [ ] 6.3 验证消歧流程 action_start 事件
  - 测试多设备消歧场景
  - 验证前端推理步骤显示完整

## 7. 归档同步

- [ ] 7.1 同步增量规格到主规格
  - 将 FR-CHAT-007、FR-CHAT-008 合并到 `openspec/specs/modbus/requirements.md`
  - 将 llm-timeout-config spec 合并或保留为独立规格

- [ ] 7.2 归档变更记录
  - 移动变更到 archive/ 目录
  - 更新 HISTORY.md
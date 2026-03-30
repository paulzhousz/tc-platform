-- ============================================================
-- Modbus 控制模块参数配置
-- 说明：从 settings.py 移至 sys_param 表的运行时可配置项
-- 执行方式：docker exec -i postgres psql -U root -d tc-platform < backend/app/plugin/module_modbus/init/init_params.sql
-- 注意：此脚本可重复执行，已存在的参数不会重复插入
-- ============================================================

-- ============================================================
-- LLM Agent 配置
-- ============================================================

INSERT INTO sys_param (config_name, config_key, config_value, config_type, status, uuid, description, created_time, updated_time)
SELECT 'LLM 模型名称', 'modbus_llm_model_name', 'Qwen/Qwen3-8B', true, '0', gen_random_uuid()::text, 'AI 助手使用的 LLM 模型', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_param WHERE config_key = 'modbus_llm_model_name');

INSERT INTO sys_param (config_name, config_key, config_value, config_type, status, uuid, description, created_time, updated_time)
SELECT 'LLM 温度参数', 'modbus_llm_temperature', '0', true, '0', gen_random_uuid()::text, 'LLM 生成温度，0=最确定性，1=最随机', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_param WHERE config_key = 'modbus_llm_temperature');

INSERT INTO sys_param (config_name, config_key, config_value, config_type, status, uuid, description, created_time, updated_time)
SELECT 'LLM 会话有效期', 'modbus_llm_session_ttl_minutes', '10', true, '0', gen_random_uuid()::text, '会话保持时间（分钟）', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_param WHERE config_key = 'modbus_llm_session_ttl_minutes');

INSERT INTO sys_param (config_name, config_key, config_value, config_type, status, uuid, description, created_time, updated_time)
SELECT 'LLM 最大历史轮数', 'modbus_llm_max_history_turns', '20', true, '0', gen_random_uuid()::text, '会话历史最大保留轮数', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_param WHERE config_key = 'modbus_llm_max_history_turns');

-- ============================================================
-- 重试配置
-- ============================================================

INSERT INTO sys_param (config_name, config_key, config_value, config_type, status, uuid, description, created_time, updated_time)
SELECT '启用自动重试', 'modbus_retry_enabled', 'true', true, '0', gen_random_uuid()::text, '操作失败时是否自动重试', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_param WHERE config_key = 'modbus_retry_enabled');

INSERT INTO sys_param (config_name, config_key, config_value, config_type, status, uuid, description, created_time, updated_time)
SELECT '重试次数', 'modbus_retry_times', '3', true, '0', gen_random_uuid()::text, '最大重试次数', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_param WHERE config_key = 'modbus_retry_times');

INSERT INTO sys_param (config_name, config_key, config_value, config_type, status, uuid, description, created_time, updated_time)
SELECT '重试间隔', 'modbus_retry_interval', '1.0', true, '0', gen_random_uuid()::text, '重试间隔时间（秒）', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_param WHERE config_key = 'modbus_retry_interval');

-- ============================================================
-- 状态轮询配置
-- ============================================================

INSERT INTO sys_param (config_name, config_key, config_value, config_type, status, uuid, description, created_time, updated_time)
SELECT '启用状态轮询', 'modbus_poll_enabled', 'true', true, '0', gen_random_uuid()::text, '是否自动轮询设备状态', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_param WHERE config_key = 'modbus_poll_enabled');

INSERT INTO sys_param (config_name, config_key, config_value, config_type, status, uuid, description, created_time, updated_time)
SELECT '轮询间隔', 'modbus_poll_interval', '5', true, '0', gen_random_uuid()::text, '状态轮询间隔（秒）', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_param WHERE config_key = 'modbus_poll_interval');

-- ============================================================
-- 待确认配置
-- ============================================================

INSERT INTO sys_param (config_name, config_key, config_value, config_type, status, uuid, description, created_time, updated_time)
SELECT '待确认过期时间', 'modbus_pending_expire_minutes', '10', true, '0', gen_random_uuid()::text, '待确认操作过期时间（分钟）', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_param WHERE config_key = 'modbus_pending_expire_minutes');

-- ============================================================
-- FunASR 语音识别配置
-- ============================================================

INSERT INTO sys_param (config_name, config_key, config_value, config_type, status, uuid, description, created_time, updated_time)
SELECT '语音识别模式', 'modbus_funasr_mode', '2pass-offline', true, '0', gen_random_uuid()::text, 'FunASR 识别模式：2pass-offline（推荐）、2pass-online', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_param WHERE config_key = 'modbus_funasr_mode');

INSERT INTO sys_param (config_name, config_key, config_value, config_type, status, uuid, description, created_time, updated_time)
SELECT '静音检测阈值', 'modbus_silence_threshold', '0.03', true, '0', gen_random_uuid()::text, '语音静音检测阈值，高于此值视为有语音', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_param WHERE config_key = 'modbus_silence_threshold');

INSERT INTO sys_param (config_name, config_key, config_value, config_type, status, uuid, description, created_time, updated_time)
SELECT '静音检测时长', 'modbus_silence_duration', '5', true, '0', gen_random_uuid()::text, '语音静音持续此时间后自动结束录音（秒）', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_param WHERE config_key = 'modbus_silence_duration');

-- ============================================================
-- 聊天历史配置
-- ============================================================

INSERT INTO sys_param (config_name, config_key, config_value, config_type, status, uuid, description, created_time, updated_time)
SELECT '聊天历史最小消息数', 'modbus_chat_save_min_messages', '2', true, '0', gen_random_uuid()::text, '新对话时，消息数达到此阈值才自动保存到历史', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM sys_param WHERE config_key = 'modbus_chat_save_min_messages');

-- ============================================================
-- 验证插入结果
-- ============================================================
SELECT 'Modbus 配置初始化完成' as result,
       (SELECT COUNT(*) FROM sys_param WHERE config_key LIKE 'modbus_%') as modbus_params_count;
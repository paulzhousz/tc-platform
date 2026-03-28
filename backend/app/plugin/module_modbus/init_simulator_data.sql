-- ============================================================
-- Modbus 仿真器设备和点位初始化数据
-- 来源: backend/app/plugin/module_modbus/modbus_simulator.py
-- ============================================================

-- ============================================================
-- 设备 1: 测试PLC设备 (Slave ID 1)
-- ============================================================
INSERT INTO modbus_devices (
    name, code, group_name, connection_type, host, port, slave_id,
    is_active, device_status, uuid, status, created_time, updated_time
) VALUES (
    '测试PLC设备', 'SIM_TEST_PLC', '仿真设备', 'TCP', '127.0.0.1', 15502, 1,
    true, 'offline', gen_random_uuid()::text, '0', NOW(), NOW()
);

-- 设备1的点位 (requires_confirmation=false)
INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '温度设定值', 'TEMP_SET', 0, 'holding', 'FLOAT', 'big', 'READ_WRITE', '℃', -40, 100, 1.0, 0.0, false, true, 1, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_TEST_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '湿度设定值', 'HUMIDITY_SET', 2, 'holding', 'FLOAT', 'big', 'READ_WRITE', '%', 0, 100, 1.0, 0.0, false, true, 2, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_TEST_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '风机频率', 'FAN_FREQ', 4, 'holding', 'FLOAT', 'big', 'READ_WRITE', 'Hz', 0, 60, 1.0, 0.0, false, true, 3, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_TEST_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '阀门开度', 'VALVE_OPEN', 6, 'holding', 'FLOAT', 'big', 'READ_WRITE', '%', 0, 100, 1.0, 0.0, false, true, 4, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_TEST_PLC';

-- 输入寄存器
INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '当前温度', 'TEMP_CURRENT', 0, 'input', 'FLOAT', 'big', 'READ', '℃', -40, 100, 1.0, 0.0, false, true, 10, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_TEST_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '当前湿度', 'HUMIDITY_CURRENT', 2, 'input', 'FLOAT', 'big', 'READ', '%', 0, 100, 1.0, 0.0, false, true, 11, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_TEST_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '当前频率', 'FREQ_CURRENT', 4, 'input', 'FLOAT', 'big', 'READ', 'Hz', 0, 60, 1.0, 0.0, false, true, 12, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_TEST_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '压力值', 'PRESSURE', 6, 'input', 'FLOAT', 'big', 'READ', 'hPa', 900, 1100, 1.0, 0.0, false, true, 13, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_TEST_PLC';

-- 线圈
INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '运行状态', 'RUN_STATUS', 0, 'coil', 'BOOL', 'big', 'READ_WRITE', NULL, 0, 1, 1.0, 0.0, false, true, 20, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_TEST_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '故障状态', 'FAULT_STATUS', 1, 'coil', 'BOOL', 'big', 'READ', NULL, 0, 1, 1.0, 0.0, false, true, 21, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_TEST_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '自动模式', 'AUTO_MODE', 2, 'coil', 'BOOL', 'big', 'READ_WRITE', NULL, 0, 1, 1.0, 0.0, false, true, 22, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_TEST_PLC';


-- ============================================================
-- 设备 2: 智能空调系统 PLC (Slave ID 2)
-- ============================================================
INSERT INTO modbus_devices (
    name, code, group_name, connection_type, host, port, slave_id,
    is_active, device_status, uuid, status, created_time, updated_time
) VALUES (
    '智能空调系统 PLC', 'SIM_AIRCOND_PLC', '仿真设备', 'TCP', '127.0.0.1', 15502, 2,
    true, 'offline', gen_random_uuid()::text, '0', NOW(), NOW()
);

-- 保持寄存器
INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '室内温度', 'INDOOR_TEMP', 0, 'holding', 'FLOAT', 'big', 'READ_WRITE', '℃', -20, 50, 1.0, 0.0, false, true, 1, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '室内湿度', 'INDOOR_HUMIDITY', 2, 'holding', 'FLOAT', 'big', 'READ_WRITE', '%', 0, 100, 1.0, 0.0, false, true, 2, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '设定温度', 'TEMP_SETPOINT', 4, 'holding', 'FLOAT', 'big', 'READ_WRITE', '℃', 16, 30, 1.0, 0.0, false, true, 3, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '风机频率', 'FAN_FREQUENCY', 6, 'holding', 'FLOAT', 'big', 'READ_WRITE', 'Hz', 0, 60, 1.0, 0.0, false, true, 4, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '阀门开度', 'VALVE_OPENING', 8, 'holding', 'FLOAT', 'big', 'READ_WRITE', '%', 0, 100, 1.0, 0.0, false, true, 5, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '回风温度', 'RETURN_AIR_TEMP', 10, 'holding', 'FLOAT', 'big', 'READ_WRITE', '℃', -20, 50, 1.0, 0.0, false, true, 6, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '送风温度', 'SUPPLY_AIR_TEMP', 12, 'holding', 'FLOAT', 'big', 'READ_WRITE', '℃', -10, 40, 1.0, 0.0, false, true, 7, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '运行模式', 'OPERATION_MODE', 14, 'holding', 'INT16', 'big', 'READ_WRITE', NULL, 0, 3, 1.0, 0.0, false, true, 8, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '设备状态', 'EQUIPMENT_STATUS', 15, 'holding', 'INT16', 'big', 'READ', NULL, 0, 2, 1.0, 0.0, false, true, 9, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

-- 输入寄存器
INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '压缩机电流', 'COMPRESSOR_CURRENT', 0, 'input', 'FLOAT', 'big', 'READ', 'A', 0, 20, 1.0, 0.0, false, true, 20, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '风机电流', 'FAN_CURRENT', 2, 'input', 'FLOAT', 'big', 'READ', 'A', 0, 10, 1.0, 0.0, false, true, 21, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '运行时长', 'RUNTIME_MINUTES', 4, 'input', 'INT32', 'big', 'READ', 'min', 0, 1000000, 1.0, 0.0, false, true, 22, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '故障代码', 'FAULT_CODE', 6, 'input', 'INT16', 'big', 'READ', NULL, 0, 100, 1.0, 0.0, false, true, 23, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

-- 线圈
INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '电源开关', 'POWER_SWITCH', 0, 'coil', 'BOOL', 'big', 'READ_WRITE', NULL, 0, 1, 1.0, 0.0, false, true, 30, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '风机启动', 'FAN_START', 1, 'coil', 'BOOL', 'big', 'READ_WRITE', NULL, 0, 1, 1.0, 0.0, false, true, 31, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '压缩机启动', 'COMPRESSOR_START', 2, 'coil', 'BOOL', 'big', 'READ_WRITE', NULL, 0, 1, 1.0, 0.0, false, true, 32, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '加热器', 'HEATER', 3, 'coil', 'BOOL', 'big', 'READ_WRITE', NULL, 0, 1, 1.0, 0.0, false, true, 33, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '新风阀', 'FRESH_AIR_DAMPER', 4, 'coil', 'BOOL', 'big', 'READ_WRITE', NULL, 0, 1, 1.0, 0.0, false, true, 34, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

-- 离散输入
INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '高温报警', 'HIGH_TEMP_ALARM', 0, 'discrete', 'BOOL', 'big', 'READ', NULL, 0, 1, 1.0, 0.0, false, true, 40, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '低温报警', 'LOW_TEMP_ALARM', 1, 'discrete', 'BOOL', 'big', 'READ', NULL, 0, 1, 1.0, 0.0, false, true, 41, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '滤网报警', 'FILTER_ALARM', 2, 'discrete', 'BOOL', 'big', 'READ', NULL, 0, 1, 1.0, 0.0, false, true, 42, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

INSERT INTO modbus_tags (device_id, name, code, address, register_type, data_type, byte_order, access_type, unit, min_value, max_value, scale_factor, "offset", requires_confirmation, is_active, sort_order, uuid, status, created_time, updated_time)
SELECT id, '漏水报警', 'WATER_LEAK_ALARM', 3, 'discrete', 'BOOL', 'big', 'READ', NULL, 0, 1, 1.0, 0.0, false, true, 43, gen_random_uuid()::text, '0', NOW(), NOW()
FROM modbus_devices WHERE code = 'SIM_AIRCOND_PLC';

-- ============================================================
-- 完成提示
-- ============================================================
SELECT '导入完成！' as result,
       (SELECT COUNT(*) FROM modbus_devices WHERE code LIKE 'SIM_%') as devices_count,
       (SELECT COUNT(*) FROM modbus_tags WHERE device_id IN (SELECT id FROM modbus_devices WHERE code LIKE 'SIM_%')) as tags_count;
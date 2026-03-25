-- Modbus 控制模块菜单初始化脚本
-- 执行此脚本前请确保已执行数据库迁移

-- 查询最大排序值
-- SELECT MAX(`order`) FROM sys_menu WHERE parent_id IS NULL;

-- 1. 创建一级目录：Modbus控制
INSERT INTO `sys_menu` (
    `name`, `type`, `order`, `icon`, `route_name`, `route_path`,
    `component_path`, `redirect`, `hidden`, `keep_alive`, `always_show`, `title`, `affix`
) VALUES (
    'Modbus控制', 1, 200, 'ep:setting', 'Modbus', '/modbus',
    NULL, '/modbus/device', 0, 0, 1, 'Modbus控制', 0
);

-- 获取刚插入的一级目录ID
SET @modbus_menu_id = LAST_INSERT_ID();

-- 2. 创建二级菜单：设备管理
INSERT INTO `sys_menu` (
    `name`, `type`, `order`, `permission`, `icon`, `route_name`, `route_path`,
    `component_path`, `redirect`, `hidden`, `keep_alive`, `always_show`, `title`, `parent_id`, `affix`
) VALUES (
    '设备管理', 2, 1, 'modbus:device:list', 'ep:cpu', 'ModbusDevice', '/modbus/device',
    'module_modbus/device/index', NULL, 0, 1, 0, '设备管理', @modbus_menu_id, 0
);

SET @device_menu_id = LAST_INSERT_ID();

-- 设备管理按钮权限
INSERT INTO `sys_menu` (`name`, `type`, `order`, `permission`, `parent_id`) VALUES
    ('查询设备', 3, 1, 'modbus:device:query', @device_menu_id),
    ('新增设备', 3, 2, 'modbus:device:add', @device_menu_id),
    ('编辑设备', 3, 3, 'modbus:device:edit', @device_menu_id),
    ('删除设备', 3, 4, 'modbus:device:delete', @device_menu_id),
    ('查看点位', 3, 5, 'modbus:device:tags', @device_menu_id);

-- 3. 创建二级菜单：控制页面
INSERT INTO `sys_menu` (
    `name`, `type`, `order`, `permission`, `icon`, `route_name`, `route_path`,
    `component_path`, `redirect`, `hidden`, `keep_alive`, `always_show`, `title`, `parent_id`, `affix`
) VALUES (
    'AI控制', 2, 2, 'modbus:control:chat', 'ep:chat-dot-round', 'ModbusControl', '/modbus/control',
    'module_modbus/control/index', NULL, 0, 0, 0, 'AI控制', @modbus_menu_id, 0
);

SET @control_menu_id = LAST_INSERT_ID();

-- 控制页面按钮权限
INSERT INTO `sys_menu` (`name`, `type`, `order`, `permission`, `parent_id`) VALUES
    ('连接设备', 3, 1, 'modbus:control:connect', @control_menu_id),
    ('断开设备', 3, 2, 'modbus:control:disconnect', @control_menu_id),
    ('读取数据', 3, 3, 'modbus:control:read', @control_menu_id),
    ('写入数据', 3, 4, 'modbus:control:write', @control_menu_id),
    ('调整参数', 3, 5, 'modbus:control:adjust', @control_menu_id);

-- 4. 创建二级菜单：操作日志
INSERT INTO `sys_menu` (
    `name`, `type`, `order`, `permission`, `icon`, `route_name`, `route_path`,
    `component_path`, `redirect`, `hidden`, `keep_alive`, `always_show`, `title`, `parent_id`, `affix`
) VALUES (
    '操作日志', 2, 3, 'modbus:log:list', 'ep:document', 'ModbusLog', '/modbus/log',
    'module_modbus/log/index', NULL, 0, 1, 0, '操作日志', @modbus_menu_id, 0
);

SET @log_menu_id = LAST_INSERT_ID();

-- 操作日志按钮权限
INSERT INTO `sys_menu` (`name`, `type`, `order`, `permission`, `parent_id`) VALUES
    ('查看详情', 3, 1, 'modbus:log:detail', @log_menu_id),
    ('导出日志', 3, 2, 'modbus:log:export', @log_menu_id);

-- 5. 将菜单关联到管理员角色（假设角色ID为1是超级管理员）
-- 注意：根据实际角色ID调整
INSERT INTO `sys_role_menus` (`role_id`, `menu_id`)
SELECT 1, id FROM `sys_menu` WHERE `route_path` LIKE '/modbus%' OR `permission` LIKE 'modbus:%';

-- 完成提示
SELECT 'Modbus 控制模块菜单初始化完成' AS message;
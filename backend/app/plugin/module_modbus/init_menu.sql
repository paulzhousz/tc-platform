-- Modbus 控制模块菜单初始化脚本 (PostgreSQL 版本)
-- 执行此脚本前请确保已执行数据库迁移
-- 使用方法: docker exec -i postgres psql -U root -d tc-platform < init_menu.sql

-- 开始事务
BEGIN;

-- 1. 创建一级目录：Modbus控制
WITH modbus_menu AS (
    INSERT INTO "sys_menu" (
        "name", "type", "order", "icon", "route_name", "route_path",
        "component_path", "redirect", "hidden", "keep_alive", "always_show", "title", "affix",
        "uuid", "status", "created_time", "updated_time"
    ) VALUES (
        'Modbus控制', 1, 200, 'ep:setting', 'Modbus', '/modbus',
        NULL, '/modbus/device', false, false, true, 'Modbus控制', false,
        'modbus-menu-root', '1', NOW(), NOW()
    ) RETURNING id
),
-- 2. 创建二级菜单：设备管理
device_menu AS (
    INSERT INTO "sys_menu" (
        "name", "type", "order", "permission", "icon", "route_name", "route_path",
        "component_path", "redirect", "hidden", "keep_alive", "always_show", "title", "parent_id", "affix",
        "uuid", "status", "created_time", "updated_time"
    ) SELECT
        '设备管理', 2, 1, 'module_modbus:device:query', 'ep:cpu', 'ModbusDevice', '/modbus/device',
        'module_modbus/device/index', NULL, false, true, false, '设备管理', id, false,
        'modbus-menu-device', '1', NOW(), NOW()
    FROM modbus_menu
    RETURNING id
),
-- 设备管理按钮权限
device_perms AS (
    INSERT INTO "sys_menu" ("name", "type", "order", "permission", "parent_id", "uuid", "status", "hidden", "keep_alive", "always_show", "affix", "created_time", "updated_time")
    SELECT perm.name, perm.type, perm.ord, perm.permission, dm.id, perm.uuid, '1', false, true, false, false, NOW(), NOW()
    FROM device_menu dm
    CROSS JOIN (VALUES
        ('查询设备', 3, 1, 'module_modbus:device:query', 'modbus-perm-device-query'),
        ('新增设备', 3, 2, 'module_modbus:device:create', 'modbus-perm-device-create'),
        ('查看详情', 3, 3, 'module_modbus:device:detail', 'modbus-perm-device-detail'),
        ('编辑设备', 3, 4, 'module_modbus:device:update', 'modbus-perm-device-update'),
        ('删除设备', 3, 5, 'module_modbus:device:delete', 'modbus-perm-device-delete'),
        ('查询点位', 3, 6, 'module_modbus:tag:query', 'modbus-perm-tag-query'),
        ('新增点位', 3, 7, 'module_modbus:tag:create', 'modbus-perm-tag-create'),
        ('编辑点位', 3, 8, 'module_modbus:tag:update', 'modbus-perm-tag-update'),
        ('删除点位', 3, 9, 'module_modbus:tag:delete', 'modbus-perm-tag-delete')
    ) AS perm(name, type, ord, permission, uuid)
),
-- 3. 创建二级菜单：控制页面
control_menu AS (
    INSERT INTO "sys_menu" (
        "name", "type", "order", "permission", "icon", "route_name", "route_path",
        "component_path", "redirect", "hidden", "keep_alive", "always_show", "title", "parent_id", "affix",
        "uuid", "status", "created_time", "updated_time"
    ) SELECT
        'AI控制', 2, 2, 'module_modbus:control:query', 'ep:chat-dot-round', 'ModbusControl', '/modbus/control',
        'module_modbus/control/index', NULL, false, false, false, 'AI控制', id, false,
        'modbus-menu-control', '1', NOW(), NOW()
    FROM modbus_menu
    RETURNING id
),
-- 控制页面按钮权限
control_perms AS (
    INSERT INTO "sys_menu" ("name", "type", "order", "permission", "parent_id", "uuid", "status", "hidden", "keep_alive", "always_show", "affix", "created_time", "updated_time")
    SELECT perm.name, perm.type, perm.ord, perm.permission, cm.id, perm.uuid, '1', false, true, false, false, NOW(), NOW()
    FROM control_menu cm
    CROSS JOIN (VALUES
        ('查询状态', 3, 1, 'module_modbus:control:query', 'modbus-perm-control-query'),
        ('连接设备', 3, 2, 'module_modbus:control:write', 'modbus-perm-control-connect'),
        ('读取数据', 3, 3, 'module_modbus:control:read', 'modbus-perm-control-read'),
        ('写入数据', 3, 4, 'module_modbus:control:write', 'modbus-perm-control-write')
    ) AS perm(name, type, ord, permission, uuid)
),
-- 4. 创建二级菜单：操作日志
log_menu AS (
    INSERT INTO "sys_menu" (
        "name", "type", "order", "permission", "icon", "route_name", "route_path",
        "component_path", "redirect", "hidden", "keep_alive", "always_show", "title", "parent_id", "affix",
        "uuid", "status", "created_time", "updated_time"
    ) SELECT
        '操作日志', 2, 3, 'module_modbus:log:query', 'ep:document', 'ModbusLog', '/modbus/log',
        'module_modbus/log/index', NULL, false, true, false, '操作日志', id, false,
        'modbus-menu-log', '1', NOW(), NOW()
    FROM modbus_menu
    RETURNING id
)
-- 操作日志按钮权限
INSERT INTO "sys_menu" ("name", "type", "order", "permission", "parent_id", "uuid", "status", "hidden", "keep_alive", "always_show", "affix", "created_time", "updated_time")
SELECT perm.name, perm.type, perm.ord, perm.permission, lm.id, perm.uuid, '1', false, true, false, false, NOW(), NOW()
FROM log_menu lm
CROSS JOIN (VALUES
    ('查看详情', 3, 1, 'module_modbus:log:detail', 'modbus-perm-log-detail')
) AS perm(name, type, ord, permission, uuid);

-- 5. 将菜单关联到超级管理员角色（假设角色ID为1）
INSERT INTO "sys_role_menus" ("role_id", "menu_id")
SELECT 1, id FROM "sys_menu" WHERE "route_path" LIKE '/modbus%' OR "permission" LIKE 'module_modbus:%';

COMMIT;

-- 完成提示
SELECT COUNT(*) || ' 条 Modbus 菜单权限已初始化' AS message
FROM "sys_menu" WHERE "permission" LIKE 'module_modbus:%';
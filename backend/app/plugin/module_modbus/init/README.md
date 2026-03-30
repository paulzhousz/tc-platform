# Modbus 控制模块初始化指南

本目录包含 Modbus 控制模块的初始化脚本和仿真工具。请按照以下步骤完成模块初始化。

## 目录结构

```
init/
├── README.md                   # 本说明文档
├── init_menu.sql               # 菜单权限初始化脚本
├── init_params.sql             # 系统参数初始化脚本
├── init_simulator_data.sql     # 仿真设备数据初始化脚本
└── modbus_simulator.py         # PLC 仿真器脚本
```

## 初始化步骤

### 1. 数据库迁移（必须）

确保已完成数据库迁移，创建必要的表结构：

```bash
cd backend
uv run main.py revision --env=dev   # 生成迁移脚本（如有模型变更）
uv run main.py upgrade --env=dev    # 应用迁移
```

### 2. 初始化系统参数

将 LLM Agent 配置、重试配置、轮询配置等参数写入 `sys_param` 表：

```bash
docker exec -i postgres psql -U root -d tc-platform < backend/app/plugin/module_modbus/init/init_params.sql
```

**参数说明：**

| 参数名 | 默认值 | 说明 |
|--------|--------|------|
| `modbus_llm_model_name` | Qwen/Qwen3-8B | AI 助手使用的 LLM 模型 |
| `modbus_llm_temperature` | 0 | LLM 生成温度（0=确定性，1=随机） |
| `modbus_llm_session_ttl_minutes` | 10 | 会话保持时间（分钟） |
| `modbus_llm_max_history_turns` | 20 | 会话历史最大保留轮数 |
| `modbus_retry_enabled` | true | 操作失败时是否自动重试 |
| `modbus_retry_times` | 3 | 最大重试次数 |
| `modbus_retry_interval` | 1.0 | 重试间隔时间（秒） |
| `modbus_poll_enabled` | true | 是否自动轮询设备状态 |
| `modbus_poll_interval` | 5 | 状态轮询间隔（秒） |
| `modbus_pending_expire_minutes` | 10 | 待执行操作过期时间（分钟） |
| `modbus_silence_threshold` | 0.03 | 语音识别静音检测阈值 |
| `modbus_silence_duration` | 5 | 语音识别静音持续时间（秒） |

### 3. 初始化菜单权限

创建 Modbus 控制模块的菜单和按钮权限：

```bash
docker exec -i postgres psql -U root -d tc-platform < backend/app/plugin/module_modbus/init/init_menu.sql
```

**菜单结构：**

```
Modbus控制
├── 设备管理        # 设备和点位 CRUD
│   ├── 查询设备
│   ├── 新增设备
│   ├── 查看详情
│   ├── 编辑设备
│   ├── 删除设备
│   ├── 查询点位
│   ├── 新增点位
│   ├── 编辑点位
│   └── 删除点位
├── 智能控制        # AI 助手对话界面
│   ├── 查询状态
│   ├── 连接设备
│   ├── 读取数据
│   └── 写入数据
└── 操作日志        # 操作记录查询
    └── 查看详情
```

### 4. 初始化仿真设备数据（可选）

如需测试 AI 控制功能，可导入仿真设备数据：

```bash
docker exec -i postgres psql -U root -d tc-platform < backend/app/plugin/module_modbus/init/init_simulator_data.sql
```

**仿真设备包括：**

| 设备名称 | IP 地址 | 端口 | 从站ID | 点位数量 |
|----------|---------|------|--------|----------|
| 温度传感器 | 127.0.0.1 | 15502 | 1 | 3 个温度测点 |
| 变频器控制 | 127.0.0.1 | 15502 | 2 | 4 个控制点位 |
| 压力变送器 | 127.0.0.1 | 15502 | 3 | 2 个压力测点 |

### 5. 启动 PLC 仿真器（可选）

启动 Modbus TCP 仿真器，模拟真实 PLC 设备：

```bash
cd backend
uv run python app/plugin/module_modbus/init/modbus_simulator.py
```

**参数选项：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--host` | 127.0.0.1 | 仿真器监听地址 |
| `--port` | 15502 | 仿真器监听端口 |
| `--slave-ids` | 1 2 3 | 模拟的从站 ID 列表 |

**示例：**

```bash
# 默认启动（监听 127.0.0.1:15502，从站 ID 1, 2, 3）
uv run python app/plugin/module_modbus/init/modbus_simulator.py

# 自定义配置
uv run python app/plugin/module_modbus/init/modbus_simulator.py --port 15503 --slave-ids 1 2
```

## 完整初始化流程

新环境一键初始化：

```bash
# 1. 数据库迁移
cd backend
uv run main.py upgrade --env=dev

# 2. 初始化参数
docker exec -i postgres psql -U root -d tc-platform < app/plugin/module_modbus/init/init_params.sql

# 3. 初始化菜单
docker exec -i postgres psql -U root -d tc-platform < app/plugin/module_modbus/init/init_menu.sql

# 4. 初始化仿真数据（可选）
docker exec -i postgres psql -U root -d tc-platform < app/plugin/module_modbus/init/init_simulator_data.sql

# 5. 启动仿真器（可选）
uv run python app/plugin/module_modbus/init/modbus_simulator.py &

# 6. 启动后端服务
uv run main.py run --env=dev
```

## 注意事项

1. **脚本可重复执行**：所有 SQL 脚本使用 `INSERT ... WHERE NOT EXISTS` 模式，不会重复插入数据。

2. **菜单关联角色**：`init_menu.sql` 会自动将菜单权限关联到超级管理员角色（ID=1）。如需关联其他角色，请在 `sys_role_menus` 表中手动添加关联。

3. **仿真器依赖**：`modbus_simulator.py` 需要 `pymodbus>=3.8.0`，请确保已安装：
   ```bash
   uv add pymodbus>=3.8.0
   ```

4. **生产环境**：生产环境无需运行仿真器和仿真数据脚本，仅执行步骤 1-3 即可。

## 相关配置文件

模块运行时配置位于 `config/` 目录：

```
config/
├── modbus_quick_commands.json   # 快捷指令配置
├── modbus_system_prompt.md      # AI 助手系统提示词
```

可在管理后台「系统参数」页面调整运行参数。
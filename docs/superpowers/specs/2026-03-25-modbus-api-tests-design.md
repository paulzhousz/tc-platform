# Modbus 模块 API 测试设计文档

## 1. 概述

### 1.1 目标

为 `backend/app/plugin/module_modbus/control/controller.py` 中的所有 API 端点编写完整的集成测试，确保 API 功能正常、稳定。

### 1.2 范围

| 模块 | 端点数 | 测试用例数 |
|------|--------|-----------|
| DeviceRouter | 9 | 18 |
| ControlRouter | 12 | 22 |
| LogRouter | 2 | 11 |
| PendingRouter | 3 | 11 |
| WebSocket | 1 | 5 |
| **总计** | **27** | **67** |

### 1.3 测试策略

- **测试类型**: API 集成测试
- **认证方式**: Mock `AuthPermission` 依赖，注入测试用户
- **外部依赖**: 完全 Mock（PLC 连接池、Agent 服务、PLC 服务）
- **数据隔离**: 每个测试独立，通过 Mock 数据库会话实现

## 2. 文件结构

```
backend/tests/module_modbus/
├── __init__.py
├── conftest.py              # 共享 fixtures
├── test_schemas.py          # ✅ 已存在
├── test_sync_plc_service.py # ✅ 已存在
├── test_device_api.py       # 设备管理 API
├── test_control_api.py      # PLC 控制 API
├── test_log_api.py          # 操作日志 API
├── test_pending_api.py      # 待确认操作 API
└── test_websocket.py        # WebSocket 端点
```

## 3. Fixtures 设计

### 3.1 认证相关

```python
@pytest.fixture
def mock_user():
    """Mock 测试用户"""
    user = MagicMock()
    user.id = 1
    user.username = "test_admin"
    user.is_superuser = True
    return user

@pytest.fixture
def mock_auth(mock_user):
    """Mock AuthSchema 认证对象"""
    auth = MagicMock()
    auth.user = mock_user
    auth.db = AsyncMock()
    return auth

@pytest.fixture
def mock_auth_dependency(mock_auth):
    """Mock AuthPermission 依赖"""
    with patch("app.plugin.module_modbus.control.controller.AuthPermission") as mock:
        mock.return_value = mock_auth
        yield mock_auth
```

### 3.2 外部依赖 Mock

```python
@pytest.fixture
def mock_connection_pool():
    """Mock PLC 连接池"""
    with patch("app.plugin.module_modbus.control.controller.connection_pool") as mock:
        mock.acquire.return_value = MagicMock()
        mock.release.return_value = None
        mock.add_device.return_value = None
        mock.remove_device.return_value = None
        mock.health_check.return_value = {"healthy": True, "available_connections": 5}
        yield mock

@pytest.fixture
def mock_plc_service():
    """Mock PLC 服务"""
    with patch("app.plugin.module_modbus.control.controller.PLCService") as mock:
        instance = mock.return_value
        instance.read = AsyncMock(return_value={
            "success": True,
            "value": 25.5,
            "raw_value": 255,
            "unit": "°C"
        })
        instance.write = AsyncMock(return_value={
            "success": True,
            "value": 50.0,
            "message": "写入成功"
        })
        yield instance

@pytest.fixture
def mock_agent_service():
    """Mock Agent 服务（LLM）"""
    with patch("app.plugin.module_modbus.control.controller.AgentService") as mock:
        instance = mock.return_value
        instance.chat = AsyncMock(return_value={
            "message": "已读取温度值 25.5°C",
            "steps": []
        })
        instance.stream_chat = AsyncMock(return_value=iter([]))
        yield instance
```

### 3.3 测试数据

```python
@pytest.fixture
def sample_device_data():
    """测试设备数据"""
    return {
        "name": "测试PLC",
        "code": "PLC_001",
        "host": "192.168.1.100",
        "port": 502,
        "slave_id": 1,
        "connection_type": "TCP",
        "description": "测试用PLC设备"
    }

@pytest.fixture
def sample_tag_data():
    """测试点位数据"""
    return {
        "name": "温度传感器",
        "code": "TEMP_001",
        "address": 40001,
        "register_type": "holding",
        "data_type": "FLOAT",
        "unit": "°C",
        "scale_factor": 0.1,
        "offset": 0.0
    }
```

## 4. 测试用例设计

### 4.1 test_device_api.py

#### 设备列表

| 测试用例 | 说明 |
|---------|------|
| `test_list_devices_success` | 正常获取设备列表 |
| `test_list_devices_empty` | 空列表场景 |

#### 设备创建

| 测试用例 | 说明 |
|---------|------|
| `test_create_device_success` | 正常创建设备 |
| `test_create_device_duplicate_code` | 编码重复，返回错误 |
| `test_create_device_invalid_port` | 端口超出范围，校验失败 |
| `test_create_device_missing_required` | 缺少必填字段 |

#### 设备详情

| 测试用例 | 说明 |
|---------|------|
| `test_get_device_success` | 正常获取详情 |
| `test_get_device_not_found` | 设备不存在 |

#### 设备更新

| 测试用例 | 说明 |
|---------|------|
| `test_update_device_success` | 正常更新 |
| `test_update_device_not_found` | 设备不存在 |
| `test_update_device_partial` | 部分字段更新 |

#### 设备删除

| 测试用例 | 说明 |
|---------|------|
| `test_delete_device_success` | 正常删除单个/多个设备 |

#### 设备连接测试

| 测试用例 | 说明 |
|---------|------|
| `test_test_connection_success` | 连接成功 |
| `test_test_connection_failed` | 连接失败 |
| `test_test_connection_device_not_found` | 设备不存在 |

#### 点位管理

| 测试用例 | 说明 |
|---------|------|
| `test_list_tags_success` | 获取点位列表 |
| `test_create_tag_success` | 创建点位 |
| `test_create_tag_duplicate_code` | 点位编码重复 |
| `test_update_tag_success` | 更新点位 |
| `test_delete_tags_success` | 删除点位 |

### 4.2 test_control_api.py

#### 设备连接

| 测试用例 | 说明 |
|---------|------|
| `test_connect_all_devices_success` | 连接所有活跃设备 |
| `test_connect_specific_devices` | 连接指定设备 |
| `test_connect_no_devices` | 无可连接设备 |
| `test_connect_partial_failure` | 部分设备连接失败 |

#### 设备断开

| 测试用例 | 说明 |
|---------|------|
| `test_disconnect_specific_devices` | 断开指定设备 |
| `test_disconnect_all_devices` | 断开所有设备 |

#### 连接状态

| 测试用例 | 说明 |
|---------|------|
| `test_get_connection_status_success` | 获取连接状态 |
| `test_get_connection_status_empty` | 无活跃设备 |

#### 聊天接口

| 测试用例 | 说明 |
|---------|------|
| `test_chat_success` | 同步聊天成功 |
| `test_chat_with_session_id` | 带会话ID的聊天 |
| `test_chat_empty_message` | 空消息校验 |

#### 流式聊天

| 测试用例 | 说明 |
|---------|------|
| `test_chat_stream_success` | SSE 流式响应 |

#### 直接读取

| 测试用例 | 说明 |
|---------|------|
| `test_read_plc_success` | 正常读取点位 |
| `test_read_plc_device_not_found` | 设备不存在 |
| `test_read_plc_tag_not_found` | 点位不存在 |

#### 直接写入

| 测试用例 | 说明 |
|---------|------|
| `test_write_plc_success` | 正常写入点位 |
| `test_write_plc_requires_confirmation` | 写入需要确认 |
| `test_write_plc_failed` | 写入失败 |

#### 快捷指令

| 测试用例 | 说明 |
|---------|------|
| `test_get_quick_commands_success` | 获取快捷指令配置 |
| `test_get_quick_commands_file_not_found` | 配置文件不存在 |

#### 聊天历史

| 测试用例 | 说明 |
|---------|------|
| `test_get_chat_history_list` | 获取历史列表 |
| `test_get_chat_history_detail` | 获取历史详情 |
| `test_save_chat_history` | 保存聊天历史 |
| `test_delete_chat_history` | 删除聊天历史 |
| `test_clear_all_chat_history` | 清空所有历史 |

### 4.3 test_log_api.py

#### 日志列表

| 测试用例 | 说明 |
|---------|------|
| `test_list_logs_success` | 正常获取日志列表 |
| `test_list_logs_with_pagination` | 分页查询 |
| `test_list_logs_filter_by_device` | 按设备ID筛选 |
| `test_list_logs_filter_by_user` | 按用户ID筛选 |
| `test_list_logs_filter_by_action` | 按操作类型筛选 |
| `test_list_logs_filter_by_status` | 按状态筛选 |
| `test_list_logs_filter_by_time_range` | 按时间范围筛选 |
| `test_list_logs_combined_filters` | 多条件组合筛选 |
| `test_list_logs_empty` | 空列表 |

#### 日志详情

| 测试用例 | 说明 |
|---------|------|
| `test_get_log_detail_success` | 正常获取详情 |
| `test_get_log_detail_not_found` | 日志不存在 |

### 4.4 test_pending_api.py

#### 待确认列表

| 测试用例 | 说明 |
|---------|------|
| `test_list_pending_success` | 正常获取列表 |
| `test_list_pending_filter_by_status` | 按状态筛选 |
| `test_list_pending_empty` | 空列表 |

#### 确认操作

| 测试用例 | 说明 |
|---------|------|
| `test_confirm_operation_success` | 正常确认执行 |
| `test_confirm_operation_not_found` | 记录不存在 |
| `test_confirm_operation_already_processed` | 已处理状态 |
| `test_confirm_operation_expired` | 操作已过期 |
| `test_confirm_operation_device_not_found` | 设备不存在 |
| `test_confirm_operation_tag_not_found` | 点位不存在 |
| `test_confirm_execution_failed` | 执行失败 |

#### 拒绝操作

| 测试用例 | 说明 |
|---------|------|
| `test_reject_operation_success` | 正常拒绝 |
| `test_reject_operation_not_found` | 记录不存在 |
| `test_reject_operation_already_processed` | 已处理状态 |

### 4.5 test_websocket.py

#### 连接认证

| 测试用例 | 说明 |
|---------|------|
| `test_websocket_connect_without_token` | 无token拒绝连接 |
| `test_websocket_connect_invalid_token` | 无效token拒绝 |
| `test_websocket_connect_success` | 正常连接成功 |

#### 消息处理

| 测试用例 | 说明 |
|---------|------|
| `test_websocket_ping_pong` | 心跳测试 |
| `test_websocket_receive_messages` | 接收消息 |

## 5. 技术选型

| 组件 | 选择 | 说明 |
|------|------|------|
| 测试框架 | pytest | 项目已使用 |
| HTTP 客户端 | fastapi.testclient.TestClient | 同步测试，简单可靠 |
| Mock 工具 | unittest.mock | Python 标准库 |
| 异步 Mock | unittest.mock.AsyncMock | 支持 async 方法 Mock |

## 6. 依赖

无额外依赖，使用 Python 标准库 + pytest（项目已有）。

## 7. 执行方式

```bash
# 运行所有 modbus 测试
pytest backend/tests/module_modbus/ -v

# 运行单个测试文件
pytest backend/tests/module_modbus/test_device_api.py -v

# 运行特定测试用例
pytest backend/tests/module_modbus/test_device_api.py::TestDeviceAPI::test_list_devices_success -v
```

## 8. 注意事项

1. **Mock 路径**: Mock 时需要使用 controller 模块中导入的路径，而非原始模块路径
2. **异步方法**: 使用 `AsyncMock` 处理 async 方法
3. **数据库 Mock**: `mock_auth.db` 是 `AsyncMock`，需要正确配置返回值链
4. **WebSocket 测试**: 使用 `TestClient.websocket_connect()` 方法
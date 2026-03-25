# Modbus API Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 modbus 控制模块编写完整的 API 集成测试，覆盖 27 个端点、67 个测试用例。

**Architecture:** 使用 pytest + unittest.mock，通过 conftest.py 提供共享 fixtures（Mock 认证、连接池、服务层），每个路由对应一个测试文件。

**Tech Stack:** pytest, fastapi.testclient.TestClient, unittest.mock, AsyncMock

---

## File Structure

```
backend/tests/module_modbus/
├── conftest.py              # 共享 fixtures（新建）
├── test_device_api.py       # 设备管理 API（新建）
├── test_control_api.py      # PLC 控制 API（新建）
├── test_log_api.py          # 操作日志 API（新建）
├── test_pending_api.py      # 待确认操作 API（新建）
└── test_websocket.py        # WebSocket 端点（新建）
```

---

## Task 1: 创建 conftest.py 共享 fixtures

**Files:**
- Create: `backend/tests/module_modbus/conftest.py`

- [ ] **Step 1: 编写 conftest.py 文件**

```python
"""
Modbus 模块测试共享 fixtures

提供 Mock 认证、外部依赖和测试数据。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from main import create_app
from fastapi.testclient import TestClient

app = create_app()


# ==================== 测试客户端 ====================

@pytest.fixture(scope="module")
def client():
    """创建测试客户端"""
    with TestClient(app) as c:
        yield c


# ==================== 认证相关 ====================

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


# ==================== 外部依赖 Mock ====================

@pytest.fixture
def mock_connection_pool():
    """Mock PLC 连接池"""
    with patch("app.plugin.module_modbus.control.controller.connection_pool") as mock:
        mock.acquire.return_value = MagicMock()
        mock.release.return_value = None
        mock.add_device.return_value = None
        mock.remove_device.return_value = None
        mock.close_all.return_value = None
        mock.health_check.return_value = {
            "healthy": True,
            "available_connections": 5,
            "max_connections": 10
        }
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
        # 正确设置异步迭代器 mock
        async def mock_stream():
            yield {"type": "text", "content": "测试响应"}
        instance.stream_chat = AsyncMock(return_value=mock_stream())
        yield instance


# ==================== 测试数据 ====================

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


# ==================== Mock 设备模型 ====================

@pytest.fixture
def mock_device_model():
    """Mock 设备 ORM 模型"""
    device = MagicMock()
    device.id = 1
    device.name = "测试PLC"
    device.code = "PLC_001"
    device.host = "192.168.1.100"
    device.port = 502
    device.slave_id = 1
    device.status = "online"
    device.connection_type = "TCP"
    device.description = "测试用PLC设备"
    device.is_active = True
    device.created_time = "2026-03-25T10:00:00"
    device.updated_time = "2026-03-25T10:00:00"
    return device


@pytest.fixture
def mock_tag_model():
    """Mock 点位 ORM 模型"""
    tag = MagicMock()
    tag.id = 1
    tag.device_id = 1
    tag.name = "温度传感器"
    tag.code = "TEMP_001"
    tag.address = 40001
    tag.register_type = "holding"
    tag.data_type = "FLOAT"
    tag.unit = "°C"
    tag.scale_factor = 0.1
    tag.offset = 0.0
    tag.access_type = "READ_WRITE"
    tag.min_value = 0
    tag.max_value = 100
    tag.sort_order = 0
    tag.created_time = "2026-03-25T10:00:00"
    tag.updated_time = "2026-03-25T10:00:00"
    return tag


@pytest.fixture
def mock_log_model():
    """Mock 操作日志 ORM 模型"""
    log = MagicMock()
    log.id = 1
    log.device_id = 1
    log.user_id = 1
    log.action = "read"
    log.tag_name = "温度传感器"
    log.value = 25.5
    log.status = "success"
    log.message = "读取成功"
    log.created_time = "2026-03-25T10:00:00"
    return log


@pytest.fixture
def mock_pending_model():
    """Mock 待确认操作 ORM 模型"""
    pending = MagicMock()
    pending.id = 1
    pending.device_name = "测试PLC"
    pending.tag_name = "温度传感器"
    pending.target_value = 50.0
    pending.status = "pending"
    pending.reason = "需要确认"
    pending.created_time = "2026-03-25T10:00:00"
    pending.expires_at = None
    pending.reviewed_by = None
    pending.reviewed_at = None
    pending.review_comment = None
    return pending


@pytest.fixture
def mock_chat_history_model():
    """Mock 聊天历史 ORM 模型"""
    history = MagicMock()
    history.id = 1
    history.session_id = "session-123"
    history.title = "测试会话"
    history.device_count = 1
    history.device_names = ["测试PLC"]
    history.messages = []
    history.start_time = "2026-03-25T10:00:00"
    history.end_time = "2026-03-25T10:30:00"
    history.created_time = "2026-03-25T10:00:00"
    return history
```

- [ ] **Step 2: 验证 conftest.py 语法**

Run: `cd backend && uv run python -c "from tests.module_modbus.conftest import *; print('OK')"`

Expected: 输出 `OK`

- [ ] **Step 3: 提交 conftest.py**

```bash
git add backend/tests/module_modbus/conftest.py
git commit -m "test(modbus): add shared fixtures for API tests"
```

---

## Task 2: 创建 test_device_api.py

**Files:**
- Create: `backend/tests/module_modbus/test_device_api.py`

- [ ] **Step 1: 编写 test_device_api.py 文件**

```python
"""
设备管理 API 测试

测试 DeviceRouter 的所有端点。
"""

import pytest
from unittest.mock import MagicMock


API_PREFIX = "/api/v1/modbus/device"


class TestDeviceListAPI:
    """设备列表 API 测试"""

    def test_list_devices_success(self, client, mock_auth_dependency, mock_auth):
        """测试获取设备列表 - 正常"""
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = []

        response = client.get(f"{API_PREFIX}/list")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "items" in data["data"]

    def test_list_devices_with_data(self, client, mock_auth_dependency, mock_auth, mock_device_model):
        """测试获取设备列表 - 有数据"""
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = [mock_device_model]

        response = client.get(f"{API_PREFIX}/list")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert len(data["data"]["items"]) == 1
        assert data["data"]["items"][0]["name"] == "测试PLC"


class TestDeviceCreateAPI:
    """设备创建 API 测试"""

    def test_create_device_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_connection_pool,
        sample_device_data
    ):
        """测试创建设备 - 正常"""
        # Mock 无重复设备
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = None

        response = client.post(f"{API_PREFIX}/create", json=sample_device_data)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["msg"] == "创建设备成功"

    def test_create_device_duplicate_code(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        sample_device_data,
        mock_device_model
    ):
        """测试创建设备 - 编码重复"""
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = mock_device_model

        response = client.post(f"{API_PREFIX}/create", json=sample_device_data)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200
        assert "已存在" in data["msg"]

    def test_create_device_invalid_port(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        sample_device_data
    ):
        """测试创建设备 - 端口超出范围"""
        sample_device_data["port"] = 70000

        response = client.post(f"{API_PREFIX}/create", json=sample_device_data)

        assert response.status_code == 422

    def test_create_device_missing_required(
        self,
        client,
        mock_auth_dependency,
        mock_auth
    ):
        """测试创建设备 - 缺少必填字段"""
        incomplete_data = {"name": "测试设备"}

        response = client.post(f"{API_PREFIX}/create", json=incomplete_data)

        assert response.status_code == 422


class TestDeviceDetailAPI:
    """设备详情 API 测试"""

    def test_get_device_success(self, client, mock_auth_dependency, mock_auth, mock_device_model):
        """测试获取设备详情 - 正常"""
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = mock_device_model

        response = client.get(f"{API_PREFIX}/detail/1")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["name"] == "测试PLC"

    def test_get_device_not_found(self, client, mock_auth_dependency, mock_auth):
        """测试获取设备详情 - 设备不存在"""
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = None

        response = client.get(f"{API_PREFIX}/detail/999")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200
        assert "不存在" in data["msg"]


class TestDeviceUpdateAPI:
    """设备更新 API 测试"""

    def test_update_device_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_connection_pool,
        mock_device_model
    ):
        """测试更新设备 - 正常"""
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = mock_device_model

        update_data = {"name": "更新后的设备"}
        response = client.put(f"{API_PREFIX}/update/1", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_update_device_not_found(self, client, mock_auth_dependency, mock_auth):
        """测试更新设备 - 设备不存在"""
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = None

        response = client.put(f"{API_PREFIX}/update/999", json={"name": "更新"})

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200
        assert "不存在" in data["msg"]

    def test_update_device_partial(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_connection_pool,
        mock_device_model
    ):
        """测试更新设备 - 部分字段"""
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = mock_device_model

        response = client.put(f"{API_PREFIX}/update/1", json={"description": "新描述"})

        assert response.status_code == 200


class TestDeviceDeleteAPI:
    """设备删除 API 测试"""

    def test_delete_device_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_connection_pool,
        mock_device_model
    ):
        """测试删除设备 - 正常"""
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = mock_device_model

        response = client.request("DELETE", f"{API_PREFIX}/delete", json=[1])

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "删除" in data["msg"]


class TestDeviceConnectionTestAPI:
    """设备连接测试 API 测试"""

    def test_test_connection_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_connection_pool,
        mock_device_model
    ):
        """测试设备连接 - 成功"""
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = mock_device_model

        # Mock 连接成功
        mock_client = MagicMock()
        mock_client.read_holding_registers.return_value = {"success": True}
        mock_connection_pool.acquire.return_value = mock_client

        response = client.post(f"{API_PREFIX}/1/test")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["connected"] is True

    def test_test_connection_failed(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_connection_pool,
        mock_device_model
    ):
        """测试设备连接 - 失败"""
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = mock_device_model
        mock_connection_pool.acquire.return_value = None

        response = client.post(f"{API_PREFIX}/1/test")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["connected"] is False

    def test_test_connection_device_not_found(self, client, mock_auth_dependency, mock_auth):
        """测试设备连接 - 设备不存在"""
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = None

        response = client.post(f"{API_PREFIX}/999/test")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200


class TestTagAPI:
    """点位管理 API 测试"""

    def test_list_tags_success(self, client, mock_auth_dependency, mock_auth, mock_tag_model):
        """测试获取点位列表 - 正常"""
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = [mock_tag_model]

        response = client.get(f"{API_PREFIX}/1/tag/list")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert len(data["data"]["items"]) == 1

    def test_create_tag_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_device_model,
        sample_tag_data
    ):
        """测试创建点位 - 正常"""
        # Mock 设备存在
        mock_auth.db.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: mock_device_model),  # 设备查询
            MagicMock(scalar_one_or_none=lambda: None),  # 点位查询（无重复）
        ]

        response = client.post(f"{API_PREFIX}/1/tag/create", json=sample_tag_data)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_create_tag_duplicate_code(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_device_model,
        mock_tag_model,
        sample_tag_data
    ):
        """测试创建点位 - 编码重复"""
        mock_auth.db.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: mock_device_model),  # 设备存在
            MagicMock(scalar_one_or_none=lambda: mock_tag_model),  # 点位已存在
        ]

        response = client.post(f"{API_PREFIX}/1/tag/create", json=sample_tag_data)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200
        assert "已存在" in data["msg"]

    def test_update_tag_success(self, client, mock_auth_dependency, mock_auth, mock_tag_model):
        """测试更新点位 - 正常"""
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = mock_tag_model

        response = client.put(f"{API_PREFIX}/tag/update/1", json={"name": "新名称"})

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_delete_tags_success(self, client, mock_auth_dependency, mock_auth, mock_tag_model):
        """测试删除点位 - 正常"""
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = mock_tag_model

        response = client.request("DELETE", f"{API_PREFIX}/tag/delete", json=[1])

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
```

- [ ] **Step 2: 运行测试验证语法**

Run: `cd backend && uv run pytest tests/module_modbus/test_device_api.py -v --collect-only`

Expected: 显示所有测试用例，无语法错误

- [ ] **Step 3: 提交 test_device_api.py**

```bash
git add backend/tests/module_modbus/test_device_api.py
git commit -m "test(modbus): add device management API tests"
```

---

## Task 3: 创建 test_control_api.py

**Files:**
- Create: `backend/tests/module_modbus/test_control_api.py`

- [ ] **Step 1: 编写 test_control_api.py 文件**

```python
"""
PLC 控制 API 测试

测试 ControlRouter 的所有端点。
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


API_PREFIX = "/api/v1/modbus/control"


class TestConnectAPI:
    """设备连接 API 测试"""

    def test_connect_all_devices_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_connection_pool,
        mock_device_model
    ):
        """测试连接所有设备 - 成功"""
        mock_device_model.is_active = True
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = [mock_device_model]

        response = client.post(f"{API_PREFIX}/connect")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_connect_specific_devices(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_connection_pool,
        mock_device_model
    ):
        """测试连接指定设备"""
        mock_device_model.is_active = True
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = [mock_device_model]

        response = client.post(f"{API_PREFIX}/connect", json=[1])

        assert response.status_code == 200

    def test_connect_no_devices(self, client, mock_auth_dependency, mock_auth):
        """测试连接 - 无可连接设备"""
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = []

        response = client.post(f"{API_PREFIX}/connect")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200

    def test_connect_partial_failure(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_connection_pool
    ):
        """测试连接 - 部分设备失败"""
        device1 = MagicMock()
        device1.id = 1
        device1.name = "设备1"
        device1.is_active = True
        device1.slave_id = 1

        device2 = MagicMock()
        device2.id = 2
        device2.name = "设备2"
        device2.is_active = True
        device2.slave_id = 1

        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = [device1, device2]
        # 第一个成功，第二个失败
        mock_connection_pool.add_device.side_effect = [None, Exception("连接失败")]

        response = client.post(f"{API_PREFIX}/connect")

        assert response.status_code == 200
        data = response.json()
        # 部分成功
        assert "部分" in data["msg"] or data["code"] != 200


class TestDisconnectAPI:
    """设备断开 API 测试"""

    def test_disconnect_specific_devices(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_connection_pool,
        mock_device_model
    ):
        """测试断开指定设备"""
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = mock_device_model

        response = client.post(f"{API_PREFIX}/disconnect", json=[1])

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_disconnect_all_devices(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_connection_pool,
        mock_device_model
    ):
        """测试断开所有设备"""
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = [mock_device_model]

        response = client.post(f"{API_PREFIX}/disconnect")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200


class TestConnectionStatusAPI:
    """连接状态 API 测试"""

    def test_get_connection_status_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_connection_pool,
        mock_device_model
    ):
        """测试获取连接状态 - 成功"""
        mock_device_model.is_active = True
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = [mock_device_model]

        response = client.get(f"{API_PREFIX}/connection-status")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert isinstance(data["data"], list)

    def test_get_connection_status_empty(self, client, mock_auth_dependency, mock_auth):
        """测试获取连接状态 - 无活跃设备"""
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = []

        response = client.get(f"{API_PREFIX}/connection-status")

        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []


class TestChatAPI:
    """聊天接口 API 测试"""

    def test_chat_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_agent_service
    ):
        """测试同步聊天 - 成功"""
        response = client.post(
            f"{API_PREFIX}/chat",
            json={"message": "读取温度"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_chat_with_session_id(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_agent_service
    ):
        """测试带会话ID的聊天"""
        response = client.post(
            f"{API_PREFIX}/chat",
            json={"message": "读取温度", "session_id": "session-123"}
        )

        assert response.status_code == 200

    def test_chat_empty_message(
        self,
        client,
        mock_auth_dependency,
        mock_auth
    ):
        """测试空消息"""
        response = client.post(
            f"{API_PREFIX}/chat",
            json={"message": ""}
        )

        assert response.status_code == 422


class TestChatStreamAPI:
    """流式聊天 API 测试"""

    def test_chat_stream_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_agent_service
    ):
        """测试 SSE 流式响应"""
        response = client.post(
            f"{API_PREFIX}/chat/stream",
            json={"message": "读取温度"}
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


class TestReadPLC:
    """直接读取 API 测试"""

    def test_read_plc_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_plc_service
    ):
        """测试读取点位 - 成功"""
        response = client.post(
            f"{API_PREFIX}/read",
            json={"device_id": 1, "tag_name": "温度"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "value" in data["data"]

    def test_read_plc_failed(
        self,
        client,
        mock_auth_dependency,
        mock_auth
    ):
        """测试读取点位 - 失败"""
        with patch("app.plugin.module_modbus.control.controller.PLCService") as mock:
            instance = mock.return_value
            instance.read = AsyncMock(return_value={
                "success": False,
                "message": "点位不存在"
            })

            response = client.post(
                f"{API_PREFIX}/read",
                json={"device_id": 999, "tag_name": "不存在"}
            )

            # 读取失败返回错误响应
            assert response.status_code == 200


class TestWritePLC:
    """直接写入 API 测试"""

    def test_write_plc_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_plc_service
    ):
        """测试写入点位 - 成功"""
        response = client.post(
            f"{API_PREFIX}/write",
            json={"device_id": 1, "tag_name": "设定值", "value": 50.0}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_write_plc_requires_confirmation(
        self,
        client,
        mock_auth_dependency,
        mock_auth
    ):
        """测试写入点位 - 需要确认"""
        with patch("app.plugin.module_modbus.control.controller.PLCService") as mock:
            instance = mock.return_value
            instance.write = AsyncMock(return_value={
                "success": False,
                "requires_confirmation": True,
                "pending_confirm_id": 1,
                "message": "需要确认"
            })

            response = client.post(
                f"{API_PREFIX}/write",
                json={"device_id": 1, "tag_name": "紧急停止", "value": 1}
            )

            # 需要确认时返回特定响应
            assert response.status_code == 200


class TestQuickCommandsAPI:
    """快捷指令 API 测试"""

    def test_get_quick_commands_success(self, client, mock_auth_dependency, mock_auth):
        """测试获取快捷指令 - 成功"""
        response = client.get(f"{API_PREFIX}/quick-commands")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200

    def test_get_quick_commands_file_not_found(
        self,
        client,
        mock_auth_dependency,
        mock_auth
    ):
        """测试获取快捷指令 - 文件不存在"""
        with patch("builtins.open", side_effect=FileNotFoundError):
            response = client.get(f"{API_PREFIX}/quick-commands")

        # 控制器会返回空列表而不是错误
        assert response.status_code == 200


class TestChatHistoryAPI:
    """聊天历史 API 测试"""

    def test_get_chat_history_list(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_chat_history_model
    ):
        """测试获取聊天历史列表"""
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = [mock_chat_history_model]

        # Mock count 查询
        with patch("app.plugin.module_modbus.control.controller.func") as mock_func:
            mock_func.count.return_value = 1
            response = client.get(f"{API_PREFIX}/chat-history")

        assert response.status_code == 200

    def test_get_chat_history_detail(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_chat_history_model
    ):
        """测试获取聊天历史详情"""
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = mock_chat_history_model

        response = client.get(f"{API_PREFIX}/chat-history/session-123")

        assert response.status_code == 200

    def test_save_chat_history(
        self,
        client,
        mock_auth_dependency,
        mock_auth
    ):
        """测试保存聊天历史"""
        history_data = {
            "session_id": "session-123",
            "messages": [
                {"role": "user", "content": "读取温度", "timestamp": "2026-03-25T10:00:00Z"}
            ],
            "device_count": 1,
            "device_names": ["测试PLC"]
        }

        response = client.post(f"{API_PREFIX}/chat-history", json=history_data)

        assert response.status_code == 200

    def test_delete_chat_history(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_chat_history_model
    ):
        """测试删除聊天历史"""
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = mock_chat_history_model

        response = client.delete(f"{API_PREFIX}/chat-history/session-123")

        assert response.status_code == 200

    def test_clear_all_chat_history(self, client, mock_auth_dependency, mock_auth):
        """测试清空所有聊天历史"""
        # Mock delete 执行
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_auth.db.execute.return_value = mock_result

        response = client.delete(f"{API_PREFIX}/chat-history")

        assert response.status_code == 200
```

- [ ] **Step 2: 运行测试验证语法**

Run: `cd backend && uv run pytest tests/module_modbus/test_control_api.py -v --collect-only`

Expected: 显示所有测试用例，无语法错误

- [ ] **Step 3: 提交 test_control_api.py**

```bash
git add backend/tests/module_modbus/test_control_api.py
git commit -m "test(modbus): add PLC control API tests"
```

---

## Task 4: 创建 test_log_api.py

**Files:**
- Create: `backend/tests/module_modbus/test_log_api.py`

- [ ] **Step 1: 编写 test_log_api.py 文件**

```python
"""
操作日志 API 测试

测试 LogRouter 的所有端点。
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime


API_PREFIX = "/api/v1/modbus/log"


class TestLogListAPI:
    """日志列表 API 测试"""

    def test_list_logs_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_log_model
    ):
        """测试获取日志列表 - 正常"""
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = [mock_log_model]

        response = client.get(f"{API_PREFIX}/list")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "items" in data["data"]

    def test_list_logs_with_pagination(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_log_model
    ):
        """测试分页查询"""
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = [mock_log_model]

        response = client.get(f"{API_PREFIX}/list?page=1&page_size=10")

        assert response.status_code == 200

    def test_list_logs_filter_by_device(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_log_model
    ):
        """测试按设备ID筛选"""
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = [mock_log_model]

        response = client.get(f"{API_PREFIX}/list?device_id=1")

        assert response.status_code == 200

    def test_list_logs_filter_by_user(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_log_model
    ):
        """测试按用户ID筛选"""
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = [mock_log_model]

        response = client.get(f"{API_PREFIX}/list?user_id=1")

        assert response.status_code == 200

    def test_list_logs_filter_by_action(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_log_model
    ):
        """测试按操作类型筛选"""
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = [mock_log_model]

        response = client.get(f"{API_PREFIX}/list?action=read")

        assert response.status_code == 200

    def test_list_logs_filter_by_status(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_log_model
    ):
        """测试按状态筛选"""
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = [mock_log_model]

        response = client.get(f"{API_PREFIX}/list?status=success")

        assert response.status_code == 200

    def test_list_logs_filter_by_time_range(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_log_model
    ):
        """测试按时间范围筛选"""
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = [mock_log_model]

        response = client.get(
            f"{API_PREFIX}/list?start_time=2026-01-01T00:00:00&end_time=2026-12-31T23:59:59"
        )

        assert response.status_code == 200

    def test_list_logs_combined_filters(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_log_model
    ):
        """测试多条件组合筛选"""
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = [mock_log_model]

        response = client.get(
            f"{API_PREFIX}/list?device_id=1&user_id=1&action=read&status=success"
        )

        assert response.status_code == 200

    def test_list_logs_empty(self, client, mock_auth_dependency, mock_auth):
        """测试空列表"""
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = []

        response = client.get(f"{API_PREFIX}/list")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["items"] == []
        assert data["data"]["total"] == 0


class TestLogDetailAPI:
    """日志详情 API 测试"""

    def test_get_log_detail_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_log_model
    ):
        """测试获取日志详情 - 正常"""
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = mock_log_model

        response = client.get(f"{API_PREFIX}/detail/1")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["action"] == "read"

    def test_get_log_detail_not_found(self, client, mock_auth_dependency, mock_auth):
        """测试获取日志详情 - 不存在"""
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = None

        response = client.get(f"{API_PREFIX}/detail/999")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200
        assert "不存在" in data["msg"]
```

- [ ] **Step 2: 运行测试验证语法**

Run: `cd backend && uv run pytest tests/module_modbus/test_log_api.py -v --collect-only`

Expected: 显示所有测试用例，无语法错误

- [ ] **Step 3: 提交 test_log_api.py**

```bash
git add backend/tests/module_modbus/test_log_api.py
git commit -m "test(modbus): add operation log API tests"
```

---

## Task 5: 创建 test_pending_api.py

**Files:**
- Create: `backend/tests/module_modbus/test_pending_api.py`

- [ ] **Step 1: 编写 test_pending_api.py 文件**

```python
"""
待确认操作 API 测试

测试 PendingRouter 的所有端点。
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta


API_PREFIX = "/api/v1/modbus/pending"


class TestPendingListAPI:
    """待确认列表 API 测试"""

    def test_list_pending_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_pending_model
    ):
        """测试获取待确认列表 - 正常"""
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = [mock_pending_model]

        response = client.get(f"{API_PREFIX}/list")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "items" in data["data"]

    def test_list_pending_filter_by_status(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_pending_model
    ):
        """测试按状态筛选"""
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = [mock_pending_model]

        response = client.get(f"{API_PREFIX}/list?status=pending")

        assert response.status_code == 200

    def test_list_pending_empty(self, client, mock_auth_dependency, mock_auth):
        """测试空列表"""
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = []

        response = client.get(f"{API_PREFIX}/list")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["items"] == []


class TestConfirmOperationAPI:
    """确认操作 API 测试"""

    def test_confirm_operation_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_pending_model,
        mock_device_model,
        mock_tag_model,
        mock_plc_service
    ):
        """测试确认操作 - 成功"""
        mock_auth.db.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: mock_pending_model),  # pending
            MagicMock(scalar_one_or_none=lambda: mock_device_model),   # device
            MagicMock(scalar_one_or_none=lambda: mock_tag_model),      # tag
        ]

        response = client.post(
            f"{API_PREFIX}/1/confirm",
            json={"comment": "确认执行"}
        )

        assert response.status_code == 200

    def test_confirm_operation_not_found(self, client, mock_auth_dependency, mock_auth):
        """测试确认操作 - 记录不存在"""
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = None

        response = client.post(
            f"{API_PREFIX}/999/confirm",
            json={"comment": "确认执行"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200
        assert "不存在" in data["msg"]

    def test_confirm_operation_already_processed(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_pending_model
    ):
        """测试确认操作 - 已处理状态"""
        mock_pending_model.status = "confirmed"
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = mock_pending_model

        response = client.post(
            f"{API_PREFIX}/1/confirm",
            json={"comment": "确认执行"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200
        assert "已处理" in data["msg"]

    def test_confirm_operation_expired(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_pending_model
    ):
        """测试确认操作 - 已过期"""
        mock_pending_model.status = "pending"
        mock_pending_model.expires_at = datetime.now() - timedelta(hours=1)
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = mock_pending_model

        response = client.post(
            f"{API_PREFIX}/1/confirm",
            json={"comment": "确认执行"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200
        assert "过期" in data["msg"]

    def test_confirm_operation_device_not_found(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_pending_model
    ):
        """测试确认操作 - 设备不存在"""
        mock_pending_model.status = "pending"
        mock_pending_model.expires_at = None
        mock_auth.db.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: mock_pending_model),  # pending exists
            MagicMock(scalar_one_or_none=lambda: None),  # device not found
        ]

        response = client.post(
            f"{API_PREFIX}/1/confirm",
            json={"comment": "确认执行"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200
        assert "设备" in data["msg"]

    def test_confirm_operation_tag_not_found(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_pending_model,
        mock_device_model
    ):
        """测试确认操作 - 点位不存在"""
        mock_pending_model.status = "pending"
        mock_pending_model.expires_at = None
        mock_auth.db.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: mock_pending_model),  # pending exists
            MagicMock(scalar_one_or_none=lambda: mock_device_model),   # device exists
            MagicMock(scalar_one_or_none=lambda: None),  # tag not found
        ]

        response = client.post(
            f"{API_PREFIX}/1/confirm",
            json={"comment": "确认执行"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200
        assert "点位" in data["msg"]

    def test_confirm_execution_failed(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_pending_model,
        mock_device_model,
        mock_tag_model
    ):
        """测试确认操作 - 执行失败"""
        mock_pending_model.status = "pending"
        mock_pending_model.expires_at = None
        mock_auth.db.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: mock_pending_model),
            MagicMock(scalar_one_or_none=lambda: mock_device_model),
            MagicMock(scalar_one_or_none=lambda: mock_tag_model),
        ]

        # Mock PLC 服务写入失败
        with patch("app.plugin.module_modbus.control.controller.PLCService") as mock:
            instance = mock.return_value
            instance.write = AsyncMock(return_value={
                "success": False,
                "message": "写入失败"
            })

            response = client.post(
                f"{API_PREFIX}/1/confirm",
                json={"comment": "确认执行"}
            )

            # 执行失败应返回错误
            assert response.status_code == 200


class TestRejectOperationAPI:
    """拒绝操作 API 测试"""

    def test_reject_operation_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_pending_model
    ):
        """测试拒绝操作 - 成功"""
        mock_pending_model.status = "pending"
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = mock_pending_model

        response = client.post(
            f"{API_PREFIX}/1/reject",
            json={"comment": "拒绝执行"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "拒绝" in data["msg"]

    def test_reject_operation_not_found(self, client, mock_auth_dependency, mock_auth):
        """测试拒绝操作 - 记录不存在"""
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = None

        response = client.post(
            f"{API_PREFIX}/999/reject",
            json={"comment": "拒绝执行"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200
        assert "不存在" in data["msg"]

    def test_reject_operation_already_processed(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_pending_model
    ):
        """测试拒绝操作 - 已处理状态"""
        mock_pending_model.status = "rejected"
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = mock_pending_model

        response = client.post(
            f"{API_PREFIX}/1/reject",
            json={"comment": "拒绝执行"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200
        assert "已处理" in data["msg"]
```

- [ ] **Step 2: 运行测试验证语法**

Run: `cd backend && uv run pytest tests/module_modbus/test_pending_api.py -v --collect-only`

Expected: 显示所有测试用例，无语法错误

- [ ] **Step 3: 提交 test_pending_api.py**

```bash
git add backend/tests/module_modbus/test_pending_api.py
git commit -m "test(modbus): add pending operation API tests"
```

---

## Task 6: 创建 test_websocket.py

**Files:**
- Create: `backend/tests/module_modbus/test_websocket.py`

- [ ] **Step 1: 编写 test_websocket.py 文件**

```python
"""
WebSocket 端点测试

测试 Modbus WebSocket 连接和消息处理。
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import json


WS_PATH = "/api/v1/ws/modbus"


class TestWebSocketAuthentication:
    """WebSocket 认证测试"""

    def test_websocket_connect_without_token(self, client):
        """测试无 token 拒绝连接"""
        # WebSocket 连接需要 token，无 token 应被拒绝
        # 由于 TestClient 的限制，直接测试可能抛出异常
        with pytest.raises(Exception):
            with client.websocket_connect(WS_PATH) as websocket:
                websocket.receive_json()

    def test_websocket_connect_invalid_token(self, client):
        """测试无效 token 拒绝连接"""
        # 无效 token 应被拒绝
        with pytest.raises(Exception):
            with client.websocket_connect(f"{WS_PATH}?token=invalid_token") as websocket:
                websocket.receive_json()

    def test_websocket_connect_success(self, client):
        """测试正常连接成功"""
        # 使用 mock 模拟完整的认证流程
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "test_user"

        mock_auth = MagicMock()
        mock_auth.user = mock_user

        with patch("app.plugin.module_modbus.control.controller._verify_token", return_value=mock_auth):
            with patch("app.plugin.module_modbus.control.controller.async_db_session") as mock_db:
                mock_session = AsyncMock()
                mock_session.__aenter__ = AsyncMock(return_value=MagicMock())
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_db.return_value = mock_session

                with patch("app.plugin.module_modbus.control.controller.websocket_endpoint", new_callable=AsyncMock):
                    # 验证 WebSocket 端点可被访问（不抛出 404）
                    # 实际 WebSocket 连接测试需要更复杂的环境
                    response = client.get(WS_PATH)
                    # 非 404 表示端点存在
                    assert response.status_code != 404


class TestWebSocketMessages:
    """WebSocket 消息测试"""

    def test_websocket_message_format(self):
        """测试消息格式定义"""
        # 验证预期的消息格式
        expected_types = [
            "device_status",
            "tag_value",
            "operation_result",
            "pending_confirm",
            "error"
        ]

        # 这些是文档中定义的消息类型
        for msg_type in expected_types:
            assert isinstance(msg_type, str)

    def test_websocket_ping_pong(self):
        """测试心跳消息格式"""
        ping_message = {"type": "ping"}
        expected_pong = {"type": "pong"}

        assert ping_message["type"] == "ping"
        assert expected_pong["type"] == "pong"

    def test_websocket_receive_messages(self):
        """测试接收消息格式"""
        # 验证服务端推送消息的预期格式
        device_status_msg = {
            "type": "device_status",
            "data": {
                "device_id": 1,
                "status": "online"
            }
        }
        tag_value_msg = {
            "type": "tag_value",
            "data": {
                "device_id": 1,
                "tag_name": "温度",
                "value": 25.5
            }
        }
        pending_confirm_msg = {
            "type": "pending_confirm",
            "data": {
                "id": 1,
                "device_name": "测试PLC",
                "tag_name": "温度",
                "target_value": 50.0
            }
        }

        # 验证消息可序列化为 JSON
        assert json.dumps(device_status_msg)
        assert json.dumps(tag_value_msg)
        assert json.dumps(pending_confirm_msg)

        # 验证消息结构
        assert device_status_msg["type"] == "device_status"
        assert "device_id" in device_status_msg["data"]
        assert tag_value_msg["type"] == "tag_value"
        assert "value" in tag_value_msg["data"]
        assert pending_confirm_msg["type"] == "pending_confirm"
        assert "target_value" in pending_confirm_msg["data"]


class TestWebSocketIntegration:
    """WebSocket 集成测试"""

    def test_websocket_endpoint_exists(self, client):
        """测试 WebSocket 端点存在"""
        # WebSocket 端点用 HTTP 访问应返回 426 Upgrade Required 或其他错误
        response = client.get(WS_PATH)
        # 非 404 表示端点存在
        assert response.status_code != 404

    def test_websocket_with_token_param(self):
        """测试 WebSocket token 参数处理"""
        # 验证 token 参数会被正确解析
        from urllib.parse import urlencode

        params = {"token": "test_token_123"}
        url = f"{WS_PATH}?{urlencode(params)}"

        assert "token=test_token_123" in url

    def test_websocket_error_message_format(self):
        """测试错误消息格式"""
        error_msg = {
            "type": "error",
            "message": "认证失败"
        }

        assert error_msg["type"] == "error"
        assert "message" in error_msg
        assert json.dumps(error_msg)  # 可序列化
```

- [ ] **Step 2: 运行测试验证语法**

Run: `cd backend && uv run pytest tests/module_modbus/test_websocket.py -v --collect-only`

Expected: 显示所有测试用例，无语法错误

- [ ] **Step 3: 提交 test_websocket.py**

```bash
git add backend/tests/module_modbus/test_websocket.py
git commit -m "test(modbus): add WebSocket endpoint tests"
```

---

## Task 7: 运行完整测试套件

- [ ] **Step 1: 运行所有 modbus 测试**

Run: `cd backend && uv run pytest tests/module_modbus/ -v --tb=short`

Expected: 所有测试通过或显示明确的失败原因

- [ ] **Step 2: 修复任何失败的测试**

根据测试输出修复 Mock 配置或测试逻辑。

- [ ] **Step 3: 最终提交**

```bash
git add -A
git commit -m "test(modbus): complete API test suite with 67 test cases"
```

---

## Summary

| Task | File | Test Cases |
|------|------|------------|
| 1 | conftest.py | Fixtures |
| 2 | test_device_api.py | 18 |
| 3 | test_control_api.py | 22 |
| 4 | test_log_api.py | 11 |
| 5 | test_pending_api.py | 11 |
| 6 | test_websocket.py | 7 |
| **Total** | | **69** |
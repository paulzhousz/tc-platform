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
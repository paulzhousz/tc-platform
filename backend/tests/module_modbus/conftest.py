"""
Modbus 模块测试共享 fixtures

提供 Mock 认证、外部依赖和测试数据。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


# ==================== 测试专用 App 创建 ====================

@asynccontextmanager
async def test_lifespan(app) -> AsyncGenerator[Any, Any]:
    """测试专用的 lifespan，初始化必要的基础设施"""
    from fastapi_limiter import FastAPILimiter
    from unittest.mock import AsyncMock

    # 创建 Mock Redis
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.incr = AsyncMock(return_value=1)
    mock_redis.decr = AsyncMock(return_value=0)
    mock_redis.expire = AsyncMock(return_value=True)
    mock_redis.keys = AsyncMock(return_value=[])
    mock_redis.delete = AsyncMock(return_value=1)

    # 设置 app.state.redis
    app.state.redis = mock_redis

    # 初始化 FastAPILimiter
    await FastAPILimiter.init(redis=mock_redis, prefix="test_limiter:")

    yield

    # 清理
    await FastAPILimiter.close()


def create_test_app():
    """创建测试专用的 FastAPI 应用"""
    from fastapi import FastAPI
    from app.config.setting import settings
    from app.plugin.init_app import (
        register_exceptions,
        register_files,
        reset_api_docs,
    )

    # 创建 FastAPI 应用，使用测试 lifespan
    app = FastAPI(**settings.FASTAPI_CONFIG, lifespan=test_lifespan)

    from app.core.logger import setup_logging
    setup_logging()

    register_exceptions(app)
    # 不注册中间件，避免操作日志记录问题（IP 验证）

    # 注册路由
    from app.api.v1.module_common import common_router
    from app.api.v1.module_monitor import monitor_router
    from app.api.v1.module_system import system_router
    from app.core.discover import get_dynamic_router

    app.include_router(common_router)
    app.include_router(system_router)
    app.include_router(monitor_router)
    app.include_router(get_dynamic_router())

    register_files(app)
    reset_api_docs(app)

    return app


# ==================== 测试客户端 ====================

from fastapi.testclient import TestClient

# 全局变量存储当前测试的 app
_current_test_app = None


@pytest.fixture(scope="module")
def client():
    """创建测试客户端"""
    global _current_test_app

    # 在测试环境中禁用操作日志记录
    from app.config.setting import settings
    original_value = settings.OPERATION_LOG_RECORD
    settings.OPERATION_LOG_RECORD = False

    try:
        _current_test_app = create_test_app()
        with TestClient(_current_test_app) as c:
            yield c
    finally:
        settings.OPERATION_LOG_RECORD = original_value
        _current_test_app = None


# ==================== 认证相关 ====================

@pytest.fixture
def mock_user():
    """Mock 测试用户"""
    user = MagicMock()
    user.id = 1
    user.username = "test_admin"
    user.is_superuser = True
    user.status = "0"  # 正常状态
    user.roles = []
    return user


@pytest.fixture
def mock_auth(mock_user):
    """Mock AuthSchema 认证对象"""
    from datetime import datetime

    auth = MagicMock()
    auth.user = mock_user
    auth.check_data_scope = False

    # 创建共享的 execute_result，测试中可以直接修改其返回值
    auth._execute_result = MagicMock()
    auth._execute_result.scalars.return_value.all.return_value = []
    auth._execute_result.scalar.return_value = 0
    auth._execute_result.scalar_one_or_none.return_value = None

    # db 是 MagicMock，但 async 方法需要用 AsyncMock
    auth.db = MagicMock()
    auth.db.execute = AsyncMock(return_value=auth._execute_result)
    auth.db.commit = AsyncMock(return_value=None)
    auth.db.rollback = AsyncMock(return_value=None)
    auth.db.flush = AsyncMock(return_value=None)
    auth.db.merge = AsyncMock(return_value=None)

    # refresh 需要更新对象的属性
    async def mock_refresh(obj, *args, **kwargs):
        """模拟 refresh，更新对象的数据库生成属性"""
        if hasattr(obj, 'id') and obj.id is None:
            obj.id = 1
        # device_status 必须有值
        if not hasattr(obj, 'device_status') or obj.device_status is None:
            obj.device_status = "offline"
        if hasattr(obj, 'created_time') and obj.created_time is None:
            obj.created_time = datetime(2026, 3, 25, 10, 0, 0)
        if hasattr(obj, 'updated_time'):
            obj.updated_time = datetime(2026, 3, 25, 10, 0, 0)
        if hasattr(obj, 'last_seen'):
            obj.last_seen = None
        return None

    auth.db.refresh = AsyncMock(side_effect=mock_refresh)
    auth.db.add = MagicMock(return_value=None)
    auth.db.delete = AsyncMock(return_value=None)  # 必须是 AsyncMock，因为代码中使用 await db.delete()
    return auth


@pytest.fixture
def mock_auth_dependency(mock_auth):
    """使用 dependency_overrides 覆盖认证"""
    from app.core.dependencies import get_current_user

    global _current_test_app
    if _current_test_app is None:
        raise RuntimeError("测试应用未初始化，请确保 client fixture 先执行")

    app = _current_test_app

    # 创建一个返回 mock_auth 的 async 函数
    async def override_get_current_user():
        return mock_auth

    # 覆盖 get_current_user 依赖
    app.dependency_overrides[get_current_user] = override_get_current_user

    yield mock_auth

    # 清理
    app.dependency_overrides.clear()


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
    from datetime import datetime

    class MockDevice:
        def __init__(self):
            self.id = 1
            self.name = "测试PLC"
            self.code = "PLC_001"
            self.host = "192.168.1.100"
            self.port = 502
            self.slave_id = 1
            self.device_status = "online"  # 与数据库模型字段名一致
            self.connection_type = "TCP"
            self.description = "测试用PLC设备"
            self.group_name = "测试分组"
            self.baud_rate = 9600
            self.parity = "N"
            self.is_active = True
            self.last_seen = datetime(2026, 3, 25, 10, 0, 0)
            self.created_time = datetime(2026, 3, 25, 10, 0, 0)
            self.updated_time = datetime(2026, 3, 25, 10, 0, 0)

    return MockDevice()


@pytest.fixture
def mock_tag_model():
    """Mock 点位 ORM 模型"""
    from datetime import datetime

    class MockTag:
        def __init__(self):
            self.id = 1
            self.device_id = 1
            self.name = "温度传感器"
            self.code = "TEMP_001"
            self.description = "温度传感器点位"
            self.address = 40001
            self.register_type = "holding"
            self.data_type = "FLOAT"
            self.byte_order = "big"
            self.access_type = "READ_WRITE"
            self.unit = "°C"
            self.scale_factor = 0.1
            self.offset = 0.0
            self.min_value = 0
            self.max_value = 100
            self.sort_order = 0
            self.current_value = 25.5
            self.last_updated = datetime(2026, 3, 25, 10, 0, 0)
            self.created_time = datetime(2026, 3, 25, 10, 0, 0)
            self.updated_time = datetime(2026, 3, 25, 10, 0, 0)

    return MockTag()


@pytest.fixture
def mock_log_model():
    """Mock 操作日志 ORM 模型"""
    from datetime import datetime

    # 创建简单的数据类来模拟 ORM 模型
    # 使用 __dict__ 或 type() 动态创建类，避免 Pyright 警告
    class MockLog:
        def __init__(self):
            self.id = 1
            self.device_id = 1
            self.user_id = 1
            self.session_id = "session-123"
            self.tag_id = 1
            self.action = "read"
            self.request_value = 25.5
            self.actual_value = 25.5
            self.log_status = "success"
            self.error_message = None
            self.confirmation_required = False
            self.confirmed_by = None
            self.confirmed_at = None
            self.ai_reasoning = None
            self.user_input = None
            self.retry_count = 0
            self.execution_time = 0.1
            self.created_time = datetime(2026, 3, 25, 10, 0, 0)
            self.executed_at = None

    return MockLog()


@pytest.fixture
def mock_pending_model():
    """Mock 待确认操作 ORM 模型"""
    from datetime import datetime

    class MockPendingConfirm:
        def __init__(self):
            self.id = 1
            self.command_log_id = 1
            self.device_name = "测试PLC"
            self.tag_name = "温度传感器"
            self.target_value = 50.0
            self.unit = "°C"
            self.confirm_status = "pending"
            self.expires_at = None
            self.reviewed_by = None
            self.reviewed_at = None
            self.review_comment = None
            self.user_input = "将温度设为50度"
            self.ai_explanation = "用户请求修改温度设定值"
            self.created_time = datetime(2026, 3, 25, 10, 0, 0)

    return MockPendingConfirm()


@pytest.fixture
def mock_chat_history_model():
    """Mock 聊天历史 ORM 模型"""
    from datetime import datetime

    class MockChatHistory:
        def __init__(self):
            self.id = 1
            self.session_id = "session-123"
            self.title = "测试会话"
            self.device_count = 1
            self.device_names = ["测试PLC"]
            self.start_time = datetime(2026, 3, 25, 10, 0, 0)
            self.end_time = datetime(2026, 3, 25, 10, 30, 0)
            self.created_time = datetime(2026, 3, 25, 10, 0, 0)
            self.user_id = 1  # 添加 user_id 属性
            self.messages = []  # 添加 messages 属性

    return MockChatHistory()
"""
Modbus 模块 Pydantic Schemas 单元测试
"""

import pytest
from pydantic import ValidationError

from app.plugin.module_modbus.schemas import (
    ConnectionType,
    RegisterType,
    DataType,
    AccessType,
    DeviceStatus,
    DeviceCreate,
    DeviceUpdate,
    TagPointCreate,
    TagPointUpdate,
    ChatRequest,
    ReadRequest,
    WriteRequest,
    ActionStep,
)


class TestEnums:
    """枚举类型测试"""

    def test_connection_type_values(self):
        """测试连接类型枚举"""
        assert ConnectionType.TCP == "TCP"
        assert ConnectionType.RTU_OVER_TCP == "RTU_OVER_TCP"

    def test_register_type_values(self):
        """测试寄存器类型枚举"""
        assert RegisterType.HOLDING == "holding"
        assert RegisterType.INPUT == "input"
        assert RegisterType.COIL == "coil"
        assert RegisterType.DISCRETE == "discrete"

    def test_data_type_values(self):
        """测试数据类型枚举"""
        assert DataType.INT16 == "INT16"
        assert DataType.UINT16 == "UINT16"
        assert DataType.INT32 == "INT32"
        assert DataType.UINT32 == "UINT32"
        assert DataType.FLOAT == "FLOAT"
        assert DataType.BOOL == "BOOL"

    def test_device_status_values(self):
        """测试设备状态枚举"""
        assert DeviceStatus.ONLINE == "online"
        assert DeviceStatus.OFFLINE == "offline"
        assert DeviceStatus.ERROR == "error"


class TestDeviceSchemas:
    """设备 Schema 测试"""

    def test_device_create_valid(self):
        """测试有效的设备创建"""
        device = DeviceCreate(
            name="测试设备",
            code="DEVICE_001",
            host="192.168.1.100",
            port=502,
        )
        assert device.name == "测试设备"
        assert device.code == "DEVICE_001"
        assert device.host == "192.168.1.100"
        assert device.port == 502
        assert device.connection_type == ConnectionType.TCP  # 默认值
        assert device.slave_id == 1  # 默认值

    def test_device_create_missing_required(self):
        """测试缺少必填字段"""
        with pytest.raises(ValidationError) as exc_info:
            DeviceCreate(name="测试设备")
        assert "code" in str(exc_info.value)
        assert "host" in str(exc_info.value)

    def test_device_create_invalid_port(self):
        """测试无效端口"""
        with pytest.raises(ValidationError):
            DeviceCreate(
                name="测试设备",
                code="DEVICE_001",
                host="192.168.1.100",
                port=70000,  # 超出范围
            )

        with pytest.raises(ValidationError):
            DeviceCreate(
                name="测试设备",
                code="DEVICE_001",
                host="192.168.1.100",
                port=0,  # 小于最小值
            )

    def test_device_update_partial(self):
        """测试部分更新"""
        update = DeviceUpdate(name="新名称")
        assert update.name == "新名称"
        assert update.host is None
        assert update.port is None

    def test_device_update_empty(self):
        """测试空更新"""
        update = DeviceUpdate()
        assert update.name is None
        assert update.description is None


class TestTagPointSchemas:
    """点位 Schema 测试"""

    def test_tagpoint_create_valid(self):
        """测试有效的点位创建"""
        tag = TagPointCreate(
            name="温度",
            code="TEMP_001",
            address=40001,
            register_type=RegisterType.HOLDING,
            data_type=DataType.FLOAT,
        )
        assert tag.name == "温度"
        assert tag.code == "TEMP_001"
        assert tag.address == 40001
        assert tag.register_type == RegisterType.HOLDING
        assert tag.data_type == DataType.FLOAT

    def test_tagpoint_create_defaults(self):
        """测试点位默认值"""
        tag = TagPointCreate(
            name="温度",
            code="TEMP_001",
            address=100,
        )
        assert tag.register_type == RegisterType.HOLDING  # 默认
        assert tag.data_type == DataType.INT16  # 默认
        assert tag.access_type == AccessType.READ_WRITE  # 默认
        assert tag.scale_factor == 1.0  # 默认
        assert tag.offset == 0.0  # 默认

    def test_tagpoint_create_missing_required(self):
        """测试缺少必填字段"""
        with pytest.raises(ValidationError) as exc_info:
            TagPointCreate(name="温度")
        assert "code" in str(exc_info.value)
        assert "address" in str(exc_info.value)

    def test_tagpoint_create_negative_address(self):
        """测试负地址"""
        with pytest.raises(ValidationError):
            TagPointCreate(
                name="温度",
                code="TEMP_001",
                address=-1,  # 负值不允许
            )

    def test_tagpoint_update_partial(self):
        """测试部分更新"""
        update = TagPointUpdate(
            name="新名称",
            min_value=0,
            max_value=100,
        )
        assert update.name == "新名称"
        assert update.min_value == 0
        assert update.max_value == 100


class TestChatSchemas:
    """聊天相关 Schema 测试"""

    def test_chat_request_valid(self):
        """测试有效的聊天请求"""
        req = ChatRequest(message="读取温度")
        assert req.message == "读取温度"
        assert req.session_id is None

    def test_chat_request_with_session(self):
        """测试带会话ID的聊天请求"""
        req = ChatRequest(message="读取温度", session_id="session-123")
        assert req.message == "读取温度"
        assert req.session_id == "session-123"

    def test_chat_request_empty_message(self):
        """测试空消息 - 当前 schema 接受空字符串"""
        # 如果需要验证空消息，应在 schema 添加 min_length=1
        req = ChatRequest(message="")
        assert req.message == ""

    def test_read_request_valid(self):
        """测试有效的读取请求"""
        req = ReadRequest(device_id=1, tag_name="温度")
        assert req.device_id == 1
        assert req.tag_name == "温度"

    def test_write_request_valid(self):
        """测试有效的写入请求"""
        req = WriteRequest(device_id=1, tag_name="设定值", value=50.5)
        assert req.device_id == 1
        assert req.tag_name == "设定值"
        assert req.value == 50.5


class TestActionStep:
    """ActionStep Schema 测试"""

    def test_action_step_minimal(self):
        """测试最小化的 ActionStep"""
        step = ActionStep(tool="read_plc")
        assert step.tool == "read_plc"
        assert step.args == {}
        assert step.status is None
        assert step.error is None

    def test_action_step_full(self):
        """测试完整的 ActionStep"""
        step = ActionStep(
            tool="write_plc",
            args={"device_id": 1, "tag_name": "温度", "value": 50},
            status="success",
            duration_ms=150,
            result="写入成功",
        )
        assert step.tool == "write_plc"
        assert step.args["device_id"] == 1
        assert step.status == "success"
        assert step.duration_ms == 150
        assert step.result == "写入成功"
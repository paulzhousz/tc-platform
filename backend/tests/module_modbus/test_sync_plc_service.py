"""
SyncPLCService 单元测试

使用 Mock 测试 PLC 服务层逻辑，不需要实际数据库或 PLC 连接。
"""

import pytest
from unittest.mock import MagicMock, patch

from app.plugin.module_modbus.control.services.sync_plc_service import SyncPLCService
from app.plugin.module_modbus.models import DeviceModel, TagPointModel


@pytest.fixture
def mock_db():
    """Mock 数据库会话"""
    return MagicMock()


@pytest.fixture
def mock_device():
    """Mock 设备模型"""
    device = MagicMock(spec=DeviceModel)
    device.id = 1
    device.name = "测试设备"
    device.code = "DEVICE_001"
    device.status = "online"
    device.slave_id = 1
    device.host = "192.168.1.100"
    device.port = 502
    return device


@pytest.fixture
def mock_tag():
    """Mock 点位模型"""
    tag = MagicMock(spec=TagPointModel)
    tag.id = 1
    tag.name = "温度"
    tag.code = "TEMP_001"
    tag.address = 40001
    tag.register_type = "holding"
    tag.data_type = "FLOAT"
    tag.scale_factor = 0.1
    tag.offset = 0.0
    tag.unit = "°C"
    tag.min_value = 0
    tag.max_value = 100
    tag.access_type = "READ_WRITE"
    tag.requires_confirmation = False
    tag.confirmation_threshold = None
    return tag


class TestNormalizeAddress:
    """地址转换测试"""

    def test_holding_register_address(self, mock_db):
        """测试保持寄存器地址转换"""
        service = SyncPLCService(mock_db)

        # PLC 地址 40001 -> Modbus 地址 0
        assert service._normalize_address(40001, "holding") == 0
        # PLC 地址 40002 -> Modbus 地址 1
        assert service._normalize_address(40002, "holding") == 1
        # PLC 地址 41001 -> Modbus 地址 1000
        assert service._normalize_address(41001, "holding") == 1000

    def test_input_register_address(self, mock_db):
        """测试输入寄存器地址转换"""
        service = SyncPLCService(mock_db)

        # PLC 地址 30001 -> Modbus 地址 0
        assert service._normalize_address(30001, "input") == 0
        # PLC 地址 30002 -> Modbus 地址 1
        assert service._normalize_address(30002, "input") == 1

    def test_coil_address(self, mock_db):
        """测试线圈地址转换"""
        service = SyncPLCService(mock_db)

        # PLC 地址 1 -> Modbus 地址 0
        assert service._normalize_address(1, "coil") == 0
        # PLC 地址 100 -> Modbus 地址 99
        assert service._normalize_address(100, "coil") == 99

    def test_discrete_address(self, mock_db):
        """测试离散输入地址转换"""
        service = SyncPLCService(mock_db)

        # PLC 地址 1 -> Modbus 地址 0
        assert service._normalize_address(1, "discrete") == 0
        # PLC 地址 50 -> Modbus 地址 49
        assert service._normalize_address(50, "discrete") == 49

    def test_address_already_normalized(self, mock_db):
        """测试已规范化的地址"""
        service = SyncPLCService(mock_db)

        # 地址小于 PLC 编程地址范围，直接返回
        assert service._normalize_address(100, "holding") == 100


class TestValueConversion:
    """数值转换测试"""

    def test_raw_to_engineering(self, mock_db, mock_tag):
        """测试原始值到工程值转换"""
        service = SyncPLCService(mock_db)

        mock_tag.scale_factor = 0.1
        mock_tag.offset = 0.0

        # 原始值 250 -> 工程值 25.0
        result = service._convert_raw_to_engineering(250, mock_tag)
        assert result == 25.0

    def test_raw_to_engineering_with_offset(self, mock_db, mock_tag):
        """测试带偏移量的转换"""
        service = SyncPLCService(mock_db)

        mock_tag.scale_factor = 0.1
        mock_tag.offset = -50

        # 原始值 500 -> 工程值 (500 * 0.1) + (-50) = 0
        result = service._convert_raw_to_engineering(500, mock_tag)
        assert result == 0.0

    def test_engineering_to_raw(self, mock_db, mock_tag):
        """测试工程值到原始值转换"""
        service = SyncPLCService(mock_db)

        mock_tag.scale_factor = 0.1
        mock_tag.offset = 0.0

        # 工程值 25.0 -> 原始值 250
        result = service._convert_engineering_to_raw(25.0, mock_tag)
        assert result == 250

    def test_engineering_to_raw_with_offset(self, mock_db, mock_tag):
        """测试带偏移量的反向转换"""
        service = SyncPLCService(mock_db)

        mock_tag.scale_factor = 0.1
        mock_tag.offset = -50

        # 工程值 0 -> 原始值 (0 - (-50)) / 0.1 = 500
        result = service._convert_engineering_to_raw(0.0, mock_tag)
        assert result == 500


class TestCheckConfirmation:
    """确认检查测试"""

    def test_no_confirmation_required(self, mock_db, mock_tag):
        """测试不需要确认"""
        service = SyncPLCService(mock_db)

        mock_tag.requires_confirmation = False
        mock_tag.confirmation_threshold = None

        result = service._check_confirmation_required(mock_tag, 50.0)
        assert result["required"] is False

    def test_confirmation_by_config(self, mock_db, mock_tag):
        """测试配置强制确认"""
        service = SyncPLCService(mock_db)

        mock_tag.requires_confirmation = True
        mock_tag.confirmation_threshold = None

        result = service._check_confirmation_required(mock_tag, 50.0)
        assert result["required"] is True
        assert "人工确认" in result["reason"]

    def test_confirmation_by_threshold(self, mock_db, mock_tag):
        """测试阈值触发确认"""
        service = SyncPLCService(mock_db)

        mock_tag.requires_confirmation = False
        mock_tag.confirmation_threshold = 80.0

        # 值小于阈值，不需要确认
        result = service._check_confirmation_required(mock_tag, 50.0)
        assert result["required"] is False

        # 值超过阈值，需要确认
        result = service._check_confirmation_required(mock_tag, 100.0)
        assert result["required"] is True
        assert "超过确认阈值" in result["reason"]

    def test_confirmation_by_safety_keywords(self, mock_db, mock_tag):
        """测试安全关键字触发确认"""
        service = SyncPLCService(mock_db)

        mock_tag.requires_confirmation = False
        mock_tag.confirmation_threshold = None
        mock_tag.name = "紧急停止"
        mock_tag.code = "ESTOP_001"

        result = service._check_confirmation_required(mock_tag, 1.0)
        assert result["required"] is True
        assert "安全关键" in result["reason"]

    def test_confirmation_multiple_reasons(self, mock_db, mock_tag):
        """测试多个确认原因"""
        service = SyncPLCService(mock_db)

        mock_tag.requires_confirmation = True
        mock_tag.confirmation_threshold = 50.0
        mock_tag.name = "安全阀"
        mock_tag.code = "SAFETY_001"

        result = service._check_confirmation_required(mock_tag, 100.0)
        assert result["required"] is True
        # 应该包含多个原因
        assert "人工确认" in result["reason"]
        assert "超过确认阈值" in result["reason"]


class TestSearchDevices:
    """设备搜索测试"""

    def test_search_no_keyword(self, mock_db, mock_device):
        """测试无关键词搜索"""
        mock_db.execute.return_value.scalars.return_value.all.return_value = [mock_device]

        service = SyncPLCService(mock_db)
        result = service.search_devices()

        assert len(result["results"]) == 1
        assert result["results"][0]["device_name"] == "测试设备"
        assert result["disambiguation_needed"] is False

    def test_search_with_keyword(self, mock_db, mock_device):
        """测试关键词搜索"""
        mock_db.execute.return_value.scalars.return_value.all.return_value = [mock_device]

        service = SyncPLCService(mock_db)
        result = service.search_devices("测试")

        assert len(result["results"]) == 1
        assert result["results"][0]["device_name"] == "测试设备"

    def test_search_no_results(self, mock_db):
        """测试无结果搜索"""
        mock_db.execute.return_value.scalars.return_value.all.return_value = []

        service = SyncPLCService(mock_db)
        result = service.search_devices("不存在")

        assert len(result["results"]) == 0
        assert result["disambiguation_needed"] is False
        assert "未找到" in result["disambiguation_hint"]

    def test_search_multiple_devices(self, mock_db):
        """测试多设备搜索"""
        device1 = MagicMock(spec=DeviceModel)
        device1.id = 1
        device1.name = "设备A"
        device1.code = "DEVICE_A"
        device1.status = "online"

        device2 = MagicMock(spec=DeviceModel)
        device2.id = 2
        device2.name = "设备B"
        device2.code = "DEVICE_B"
        device2.status = "offline"

        mock_db.execute.return_value.scalars.return_value.all.return_value = [device1, device2]

        service = SyncPLCService(mock_db)
        result = service.search_devices("设备")

        assert len(result["results"]) == 2
        assert result["disambiguation_needed"] is True
        assert "请选择" in result["disambiguation_hint"]


class TestReadTag:
    """读取点位测试"""

    @patch("app.plugin.module_modbus.control.services.sync_plc_service.connection_pool")
    def test_read_tag_not_found(self, mock_pool, mock_db):
        """测试点位不存在"""
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        service = SyncPLCService(mock_db)
        result = service.read(1, "NOT_EXIST")

        assert result["success"] is False
        assert "未找到点位" in result["message"]

    @patch("app.plugin.module_modbus.control.services.sync_plc_service.connection_pool")
    def test_read_no_connection(self, mock_pool, mock_db, mock_tag, mock_device):
        """测试无连接"""
        # 设置点位查询返回
        mock_db.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: mock_tag),  # tag query
            MagicMock(scalar_one_or_none=lambda: mock_device),  # device query
        ]
        mock_pool.acquire.return_value = None

        service = SyncPLCService(mock_db)
        result = service.read(1, "TEMP_001")

        assert result["success"] is False
        assert "无法获取设备连接" in result["message"]


class TestWriteTag:
    """写入点位测试"""

    def test_write_tag_not_found(self, mock_db):
        """测试点位不存在"""
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        service = SyncPLCService(mock_db)
        result = service.write(1, "NOT_EXIST", 50.0)

        assert result["success"] is False
        assert "未找到点位" in result["message"]

    def test_write_readonly_tag(self, mock_db, mock_tag, mock_device):
        """测试写入只读点位"""
        mock_tag.access_type = "READ"
        mock_db.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: mock_tag),
            MagicMock(scalar_one_or_none=lambda: mock_device),
        ]

        service = SyncPLCService(mock_db)
        result = service.write(1, "TEMP_001", 50.0)

        assert result["success"] is False
        assert "只读" in result["message"]

    def test_write_out_of_range(self, mock_db, mock_tag, mock_device):
        """测试写入值超出范围"""
        mock_tag.min_value = 0
        mock_tag.max_value = 100
        mock_db.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: mock_tag),
            MagicMock(scalar_one_or_none=lambda: mock_device),
        ]

        service = SyncPLCService(mock_db)
        result = service.write(1, "TEMP_001", 150.0)

        assert result["success"] is False
        assert "超出安全范围" in result["message"]
"""
设备管理 API 测试

测试 DeviceRouter 的所有端点。
遵循 FastAPI Admin 框架规范，Mock Service 层而非数据库层。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


API_PREFIX = "/api/v1/modbus/device"


# ==================== 测试数据 ====================

def get_mock_device_response():
    """获取模拟设备响应数据"""
    return {
        "id": 1,
        "name": "测试PLC",
        "code": "PLC_001",
        "description": "测试用PLC设备",
        "group_name": "测试分组",
        "connection_type": "TCP",
        "host": "192.168.1.100",
        "port": 502,
        "slave_id": 1,
        "baud_rate": 9600,
        "parity": "N",
        "device_status": "online",
        "last_seen": datetime(2026, 3, 25, 10, 0, 0),
        "created_time": datetime(2026, 3, 25, 10, 0, 0),
        "updated_time": datetime(2026, 3, 25, 10, 0, 0),
    }


def get_mock_tag_response():
    """获取模拟点位响应数据"""
    return {
        "id": 1,
        "device_id": 1,
        "name": "温度传感器",
        "code": "TEMP_001",
        "description": "温度传感器点位",
        "address": 40001,
        "register_type": "holding",
        "data_type": "FLOAT",
        "byte_order": "big",
        "access_type": "READ_WRITE",
        "min_value": 0,
        "max_value": 100,
        "unit": "°C",
        "scale_factor": 0.1,
        "offset": 0.0,
        "aliases": [],
        "requires_confirmation": False,
        "confirmation_threshold": None,
        "sort_order": 0,
        "is_active": True,
        "current_value": 25.5,
        "last_updated": datetime(2026, 3, 25, 10, 0, 0),
        "created_time": datetime(2026, 3, 25, 10, 0, 0),
        "updated_time": datetime(2026, 3, 25, 10, 0, 0),
    }


class TestDeviceListAPI:
    """设备列表 API 测试"""

    def test_list_devices_success(self, client, mock_auth_dependency, mock_auth):
        """测试获取设备列表 - 正常"""
        with patch("app.plugin.module_modbus.device.controller.DeviceService") as mock_service:
            mock_service.list_service = AsyncMock(return_value=[])

            response = client.get(f"{API_PREFIX}/list")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "items" in data["data"]

    def test_list_devices_with_data(self, client, mock_auth_dependency, mock_auth):
        """测试获取设备列表 - 有数据"""
        mock_device = get_mock_device_response()

        with patch("app.plugin.module_modbus.device.controller.DeviceService") as mock_service:
            mock_service.list_service = AsyncMock(return_value=[mock_device])

            response = client.get(f"{API_PREFIX}/list")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
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
        mock_device = get_mock_device_response()

        with patch("app.plugin.module_modbus.device.controller.DeviceService") as mock_service:
            mock_service.create_service = AsyncMock(return_value=mock_device)

            response = client.post(f"{API_PREFIX}/create", json=sample_device_data)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["msg"] == "创建设备成功"

    def test_create_device_duplicate_code(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        sample_device_data
    ):
        """测试创建设备 - 编码重复"""
        from app.core.exceptions import CustomException
        from fastapi import status

        with patch("app.plugin.module_modbus.device.controller.DeviceService") as mock_service:
            mock_service.create_service = AsyncMock(
                side_effect=CustomException(
                    msg="设备编码 'PLC_001' 已存在",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            )

            response = client.post(f"{API_PREFIX}/create", json=sample_device_data)

        # ErrorResponse 返回 HTTP 400
        assert response.status_code == 400
        data = response.json()
        assert data["code"] != 0
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

    def test_get_device_success(self, client, mock_auth_dependency, mock_auth):
        """测试获取设备详情 - 正常"""
        mock_device = get_mock_device_response()

        with patch("app.plugin.module_modbus.device.controller.DeviceService") as mock_service:
            mock_service.detail_service = AsyncMock(return_value=mock_device)

            response = client.get(f"{API_PREFIX}/detail/1")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["name"] == "测试PLC"

    def test_get_device_not_found(self, client, mock_auth_dependency, mock_auth):
        """测试获取设备详情 - 设备不存在"""
        from app.core.exceptions import CustomException
        from fastapi import status

        with patch("app.plugin.module_modbus.device.controller.DeviceService") as mock_service:
            mock_service.detail_service = AsyncMock(
                side_effect=CustomException(
                    msg="设备不存在",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            )

            response = client.get(f"{API_PREFIX}/detail/999")

        # ErrorResponse 返回 HTTP 400
        assert response.status_code == 400
        data = response.json()
        assert data["code"] != 0
        assert "不存在" in data["msg"]


class TestDeviceUpdateAPI:
    """设备更新 API 测试"""

    def test_update_device_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_connection_pool
    ):
        """测试更新设备 - 正常"""
        mock_device = get_mock_device_response()
        mock_device["name"] = "更新后的设备"

        with patch("app.plugin.module_modbus.device.controller.DeviceService") as mock_service:
            mock_service.update_service = AsyncMock(return_value=mock_device)

            update_data = {"name": "更新后的设备"}
            response = client.put(f"{API_PREFIX}/update/1", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    def test_update_device_not_found(self, client, mock_auth_dependency, mock_auth):
        """测试更新设备 - 设备不存在"""
        from app.core.exceptions import CustomException
        from fastapi import status

        with patch("app.plugin.module_modbus.device.controller.DeviceService") as mock_service:
            mock_service.update_service = AsyncMock(
                side_effect=CustomException(
                    msg="设备不存在",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            )

            response = client.put(f"{API_PREFIX}/update/999", json={"name": "更新"})

        # ErrorResponse 返回 HTTP 400
        assert response.status_code == 400
        data = response.json()
        assert data["code"] != 0
        assert "不存在" in data["msg"]

    def test_update_device_partial(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_connection_pool
    ):
        """测试更新设备 - 部分字段"""
        mock_device = get_mock_device_response()
        mock_device["description"] = "新描述"

        with patch("app.plugin.module_modbus.device.controller.DeviceService") as mock_service:
            mock_service.update_service = AsyncMock(return_value=mock_device)

            response = client.put(f"{API_PREFIX}/update/1", json={"description": "新描述"})

        assert response.status_code == 200


class TestDeviceDeleteAPI:
    """设备删除 API 测试"""

    def test_delete_device_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_connection_pool
    ):
        """测试删除设备 - 正常"""
        with patch("app.plugin.module_modbus.device.controller.DeviceService") as mock_service:
            mock_service.delete_service = AsyncMock(return_value=None)

            response = client.request("DELETE", f"{API_PREFIX}/delete", json=[1])

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "删除" in data["msg"]


class TestDeviceConnectionTestAPI:
    """设备连接测试 API 测试"""

    def test_test_connection_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_device_model
    ):
        """测试设备连接 - 成功"""
        from app.plugin.module_modbus.control.services.connection_pool import connection_pool

        with patch("app.plugin.module_modbus.device.controller.DeviceCRUD") as mock_crud, \
             patch.object(connection_pool, 'acquire') as mock_acquire:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.get_by_id_crud = AsyncMock(return_value=mock_device_model)

            # Mock 连接成功
            mock_client = MagicMock()
            mock_client.read_holding_registers.return_value = {"success": True}
            mock_acquire.return_value = mock_client

            response = client.post(f"{API_PREFIX}/1/test")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["connected"] is True

    def test_test_connection_failed(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_device_model
    ):
        """测试设备连接 - 失败"""
        from app.plugin.module_modbus.control.services.connection_pool import connection_pool

        with patch("app.plugin.module_modbus.device.controller.DeviceCRUD") as mock_crud, \
             patch.object(connection_pool, 'acquire') as mock_acquire:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.get_by_id_crud = AsyncMock(return_value=mock_device_model)
            mock_acquire.return_value = None

            response = client.post(f"{API_PREFIX}/1/test")

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["connected"] is False

    def test_test_connection_device_not_found(self, client, mock_auth_dependency, mock_auth):
        """测试设备连接 - 设备不存在"""
        with patch("app.plugin.module_modbus.device.controller.DeviceCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.get_by_id_crud = AsyncMock(return_value=None)

            response = client.post(f"{API_PREFIX}/999/test")

        # ErrorResponse 返回 HTTP 400
        assert response.status_code == 400
        data = response.json()
        assert data["code"] != 0


class TestTagAPI:
    """点位管理 API 测试"""

    def test_list_tags_success(self, client, mock_auth_dependency, mock_auth):
        """测试获取点位列表 - 正常"""
        mock_tag = get_mock_tag_response()

        with patch("app.plugin.module_modbus.device.controller.TagPointService") as mock_service:
            mock_service.list_by_device_service = AsyncMock(return_value=[mock_tag])

            response = client.get(f"{API_PREFIX}/1/tag/list")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]["items"]) == 1

    def test_create_tag_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        sample_tag_data
    ):
        """测试创建点位 - 正常"""
        mock_tag = get_mock_tag_response()

        with patch("app.plugin.module_modbus.device.controller.TagPointService") as mock_service:
            mock_service.create_service = AsyncMock(return_value=mock_tag)

            response = client.post(f"{API_PREFIX}/1/tag/create", json=sample_tag_data)

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    def test_create_tag_duplicate_code(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        sample_tag_data
    ):
        """测试创建点位 - 编码重复"""
        from app.core.exceptions import CustomException
        from fastapi import status

        with patch("app.plugin.module_modbus.device.controller.TagPointService") as mock_service:
            mock_service.create_service = AsyncMock(
                side_effect=CustomException(
                    msg="点位编码 'TEMP_001' 已存在",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            )

            response = client.post(f"{API_PREFIX}/1/tag/create", json=sample_tag_data)

        # ErrorResponse 返回 HTTP 400
        assert response.status_code == 400
        data = response.json()
        assert data["code"] != 0
        assert "已存在" in data["msg"]

    def test_update_tag_success(self, client, mock_auth_dependency, mock_auth):
        """测试更新点位 - 正常"""
        mock_tag = get_mock_tag_response()
        mock_tag["name"] = "新名称"

        with patch("app.plugin.module_modbus.device.controller.TagPointService") as mock_service:
            mock_service.update_service = AsyncMock(return_value=mock_tag)

            response = client.put(f"{API_PREFIX}/tag/update/1", json={"name": "新名称"})

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    def test_delete_tags_success(self, client, mock_auth_dependency, mock_auth):
        """测试删除点位 - 正常"""
        with patch("app.plugin.module_modbus.device.controller.TagPointService") as mock_service:
            mock_service.delete_service = AsyncMock(return_value=None)

            response = client.request("DELETE", f"{API_PREFIX}/tag/delete", json=[1])

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
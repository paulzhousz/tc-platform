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
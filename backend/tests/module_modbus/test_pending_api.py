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

    def test_list_pending_success(self, client, mock_auth_dependency, mock_auth, mock_pending_model):
        """测试获取待确认列表 - 正常"""
        mock_pending_model.status = "pending"
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = [mock_pending_model]

        response = client.get(f"{API_PREFIX}/list")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "items" in data["data"]
        assert len(data["data"]["items"]) == 1

    def test_list_pending_filter_by_status(self, client, mock_auth_dependency, mock_auth, mock_pending_model):
        """测试获取待确认列表 - 按状态筛选"""
        mock_pending_model.status = "confirmed"
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = [mock_pending_model]

        response = client.get(f"{API_PREFIX}/list?status=confirmed")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert len(data["data"]["items"]) == 1

    def test_list_pending_empty(self, client, mock_auth_dependency, mock_auth):
        """测试获取待确认列表 - 空列表"""
        mock_auth.db.execute.return_value.scalars.return_value.all.return_value = []

        response = client.get(f"{API_PREFIX}/list")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert len(data["data"]["items"]) == 0
        assert data["data"]["total"] == 0


class TestConfirmOperationAPI:
    """确认操作 API 测试"""

    def test_confirm_operation_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_pending_model,
        mock_device_model,
        mock_tag_model
    ):
        """测试确认操作 - 正常确认执行"""
        mock_pending_model.status = "pending"
        mock_pending_model.expires_at = None
        mock_pending_model.device_name = "测试PLC"
        mock_pending_model.tag_name = "温度传感器"
        mock_pending_model.target_value = 50.0

        # Mock 数据库查询链
        mock_auth.db.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: mock_pending_model),  # pending 查询
            MagicMock(scalar_one_or_none=lambda: mock_device_model),   # device 查询
            MagicMock(scalar_one_or_none=lambda: mock_tag_model),      # tag 查询
        ]

        # Mock PLCService.write 成功
        with patch("app.plugin.module_modbus.control.controller.PLCService") as mock_plc:
            mock_instance = mock_plc.return_value
            mock_instance.write = AsyncMock(return_value={
                "success": True,
                "value": 50.0,
                "message": "写入成功"
            })

            response = client.post(f"{API_PREFIX}/1/confirm", json={"comment": "确认执行"})

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "成功" in data["msg"]

    def test_confirm_operation_not_found(self, client, mock_auth_dependency, mock_auth):
        """测试确认操作 - 记录不存在"""
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = None

        response = client.post(f"{API_PREFIX}/999/confirm", json={"comment": "确认"})

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200
        assert "不存在" in data["msg"]

    def test_confirm_operation_already_processed(self, client, mock_auth_dependency, mock_auth, mock_pending_model):
        """测试确认操作 - 已处理状态"""
        mock_pending_model.status = "confirmed"
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = mock_pending_model

        response = client.post(f"{API_PREFIX}/1/confirm", json={"comment": "确认"})

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200
        assert "已处理" in data["msg"]

    def test_confirm_operation_expired(self, client, mock_auth_dependency, mock_auth, mock_pending_model):
        """测试确认操作 - 操作已过期"""
        mock_pending_model.status = "pending"
        mock_pending_model.expires_at = datetime.now() - timedelta(hours=1)  # 已过期
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = mock_pending_model

        response = client.post(f"{API_PREFIX}/1/confirm", json={"comment": "确认"})

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
        mock_pending_model.device_name = "不存在的设备"

        mock_auth.db.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: mock_pending_model),  # pending 查询
            MagicMock(scalar_one_or_none=lambda: None),  # device 查询返回 None
        ]

        response = client.post(f"{API_PREFIX}/1/confirm", json={"comment": "确认"})

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200
        assert "设备" in data["msg"] and "不存在" in data["msg"]

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
        mock_pending_model.device_name = "测试PLC"
        mock_pending_model.tag_name = "不存在的点位"

        mock_auth.db.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: mock_pending_model),  # pending 查询
            MagicMock(scalar_one_or_none=lambda: mock_device_model),   # device 查询
            MagicMock(scalar_one_or_none=lambda: None),  # tag 查询返回 None
        ]

        response = client.post(f"{API_PREFIX}/1/confirm", json={"comment": "确认"})

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200
        assert "点位" in data["msg"] and "不存在" in data["msg"]

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
        mock_pending_model.device_name = "测试PLC"
        mock_pending_model.tag_name = "温度传感器"
        mock_pending_model.target_value = 50.0

        mock_auth.db.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: mock_pending_model),
            MagicMock(scalar_one_or_none=lambda: mock_device_model),
            MagicMock(scalar_one_or_none=lambda: mock_tag_model),
        ]

        # Mock PLCService.write 失败
        with patch("app.plugin.module_modbus.control.controller.PLCService") as mock_plc:
            mock_instance = mock_plc.return_value
            mock_instance.write = AsyncMock(return_value={
                "success": False,
                "message": "PLC 连接超时"
            })

            response = client.post(f"{API_PREFIX}/1/confirm", json={"comment": "确认执行"})

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200
        assert "失败" in data["msg"]


class TestRejectOperationAPI:
    """拒绝操作 API 测试"""

    def test_reject_operation_success(self, client, mock_auth_dependency, mock_auth, mock_pending_model):
        """测试拒绝操作 - 正常拒绝"""
        mock_pending_model.status = "pending"
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = mock_pending_model

        response = client.post(f"{API_PREFIX}/1/reject", json={"comment": "拒绝执行"})

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "拒绝" in data["msg"]

    def test_reject_operation_not_found(self, client, mock_auth_dependency, mock_auth):
        """测试拒绝操作 - 记录不存在"""
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = None

        response = client.post(f"{API_PREFIX}/999/reject", json={"comment": "拒绝"})

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200
        assert "不存在" in data["msg"]

    def test_reject_operation_already_processed(self, client, mock_auth_dependency, mock_auth, mock_pending_model):
        """测试拒绝操作 - 已处理状态"""
        mock_pending_model.status = "rejected"
        mock_auth.db.execute.return_value.scalar_one_or_none.return_value = mock_pending_model

        response = client.post(f"{API_PREFIX}/1/reject", json={"comment": "拒绝"})

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200
        assert "已处理" in data["msg"]
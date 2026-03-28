"""
待确认操作 API 测试

测试 PendingRouter 的所有端点。
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta, timezone


API_PREFIX = "/api/v1/modbus/pending"


class TestPendingListAPI:
    """待确认列表 API 测试"""

    def test_list_pending_success(self, client, mock_auth_dependency, mock_auth, mock_pending_model):
        """测试获取待确认列表 - 正常"""
        mock_pending_model.confirm_status = "pending"

        with patch("app.plugin.module_modbus.control.controller.PendingConfirmService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.list = AsyncMock(return_value={
                "items": [mock_pending_model.__dict__],
                "total": 1
            })

            response = client.get(f"{API_PREFIX}/list")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "items" in data["data"]

    def test_list_pending_filter_by_status(self, client, mock_auth_dependency, mock_auth, mock_pending_model):
        """测试获取待确认列表 - 按状态筛选"""
        mock_pending_model.confirm_status = "confirmed"

        with patch("app.plugin.module_modbus.control.controller.PendingConfirmService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.list = AsyncMock(return_value={
                "items": [mock_pending_model.__dict__],
                "total": 1
            })

            response = client.get(f"{API_PREFIX}/list?status=confirmed")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    def test_list_pending_empty(self, client, mock_auth_dependency, mock_auth):
        """测试获取待确认列表 - 空列表"""
        with patch("app.plugin.module_modbus.control.controller.PendingConfirmService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.list = AsyncMock(return_value={"items": [], "total": 0})

            response = client.get(f"{API_PREFIX}/list")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
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
        with patch("app.plugin.module_modbus.control.controller.PendingConfirmService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.confirm = AsyncMock(return_value={
                "success": True,
                "message": "操作已确认并执行",
                "result": {"value": 50.0}
            })

            response = client.post(f"{API_PREFIX}/1/confirm", json={"comment": "确认执行"})

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "成功" in data["msg"]

    def test_confirm_operation_not_found(self, client, mock_auth_dependency, mock_auth):
        """测试确认操作 - 记录不存在"""
        with patch("app.plugin.module_modbus.control.controller.PendingConfirmService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.confirm = AsyncMock(return_value={
                "success": False,
                "message": "待确认记录不存在"
            })

            response = client.post(f"{API_PREFIX}/999/confirm", json={"comment": "确认"})

        # ErrorResponse 返回 HTTP 400
        assert response.status_code == 400
        data = response.json()
        assert data["code"] != 0
        assert "不存在" in data["msg"]

    def test_confirm_operation_already_processed(self, client, mock_auth_dependency, mock_auth, mock_pending_model):
        """测试确认操作 - 已处理状态"""
        with patch("app.plugin.module_modbus.control.controller.PendingConfirmService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.confirm = AsyncMock(return_value={
                "success": False,
                "message": "该操作已处理，状态: confirmed"
            })

            response = client.post(f"{API_PREFIX}/1/confirm", json={"comment": "确认"})

        # ErrorResponse 返回 HTTP 400
        assert response.status_code == 400
        data = response.json()
        assert data["code"] != 0
        assert "已处理" in data["msg"]

    def test_confirm_operation_expired(self, client, mock_auth_dependency, mock_auth, mock_pending_model):
        """测试确认操作 - 操作已过期"""
        with patch("app.plugin.module_modbus.control.controller.PendingConfirmService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.confirm = AsyncMock(return_value={
                "success": False,
                "message": "操作已过期"
            })

            response = client.post(f"{API_PREFIX}/1/confirm", json={"comment": "确认"})

        # ErrorResponse 返回 HTTP 400
        assert response.status_code == 400
        data = response.json()
        assert data["code"] != 0
        assert "过期" in data["msg"]

    def test_confirm_operation_device_not_found(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_pending_model
    ):
        """测试确认操作 - 设备不存在"""
        with patch("app.plugin.module_modbus.control.controller.PendingConfirmService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.confirm = AsyncMock(return_value={
                "success": False,
                "message": "设备 '不存在的设备' 不存在"
            })

            response = client.post(f"{API_PREFIX}/1/confirm", json={"comment": "确认"})

        # ErrorResponse 返回 HTTP 400
        assert response.status_code == 400
        data = response.json()
        assert data["code"] != 0
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
        with patch("app.plugin.module_modbus.control.controller.PendingConfirmService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.confirm = AsyncMock(return_value={
                "success": False,
                "message": "点位 '不存在的点位' 不存在"
            })

            response = client.post(f"{API_PREFIX}/1/confirm", json={"comment": "确认"})

        # ErrorResponse 返回 HTTP 400
        assert response.status_code == 400
        data = response.json()
        assert data["code"] != 0
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
        with patch("app.plugin.module_modbus.control.controller.PendingConfirmService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.confirm = AsyncMock(return_value={
                "success": False,
                "message": "执行失败: PLC 连接超时"
            })

            response = client.post(f"{API_PREFIX}/1/confirm", json={"comment": "确认执行"})

        # ErrorResponse 返回 HTTP 400
        assert response.status_code == 400
        data = response.json()
        assert data["code"] != 0
        assert "失败" in data["msg"]


class TestRejectOperationAPI:
    """拒绝操作 API 测试"""

    def test_reject_operation_success(self, client, mock_auth_dependency, mock_auth, mock_pending_model):
        """测试拒绝操作 - 正常拒绝"""
        with patch("app.plugin.module_modbus.control.controller.PendingConfirmService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.reject = AsyncMock(return_value={
                "success": True,
                "message": "操作已拒绝"
            })

            response = client.post(f"{API_PREFIX}/1/reject", json={"comment": "拒绝执行"})

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "拒绝" in data["msg"]

    def test_reject_operation_not_found(self, client, mock_auth_dependency, mock_auth):
        """测试拒绝操作 - 记录不存在"""
        with patch("app.plugin.module_modbus.control.controller.PendingConfirmService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.reject = AsyncMock(return_value={
                "success": False,
                "message": "待确认记录不存在"
            })

            response = client.post(f"{API_PREFIX}/999/reject", json={"comment": "拒绝"})

        # ErrorResponse 返回 HTTP 400
        assert response.status_code == 400
        data = response.json()
        assert data["code"] != 0
        assert "不存在" in data["msg"]

    def test_reject_operation_already_processed(self, client, mock_auth_dependency, mock_auth, mock_pending_model):
        """测试拒绝操作 - 已处理状态"""
        with patch("app.plugin.module_modbus.control.controller.PendingConfirmService") as mock_service:
            mock_instance = mock_service.return_value
            mock_instance.reject = AsyncMock(return_value={
                "success": False,
                "message": "该操作已处理，状态: rejected"
            })

            response = client.post(f"{API_PREFIX}/1/reject", json={"comment": "拒绝"})

        # ErrorResponse 返回 HTTP 400
        assert response.status_code == 400
        data = response.json()
        assert data["code"] != 0
        assert "已处理" in data["msg"]
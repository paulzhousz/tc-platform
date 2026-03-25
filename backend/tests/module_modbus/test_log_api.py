"""
操作日志 API 测试

测试 LogRouter 的所有端点。
"""

import pytest
from unittest.mock import MagicMock


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
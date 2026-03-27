"""
PendingConfirmService 单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.plugin.module_modbus.control.services.pending_confirm_service import PendingConfirmService
from app.plugin.module_modbus.schemas import ConfirmAction


class TestPendingConfirmServiceList:
    """list 方法测试"""

    @pytest.mark.asyncio
    async def test_list_success(self, mock_auth, mock_pending_model):
        """测试获取列表 - 正常"""
        with patch("app.plugin.module_modbus.control.services.pending_confirm_service.PendingConfirmCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.list_pending = AsyncMock(return_value=[mock_pending_model])

            service = PendingConfirmService(mock_auth.db, MagicMock())
            result = await service.list()

            assert "items" in result
            assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_list_empty(self, mock_auth):
        """测试获取列表 - 空列表"""
        with patch("app.plugin.module_modbus.control.services.pending_confirm_service.PendingConfirmCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.list_pending = AsyncMock(return_value=[])

            service = PendingConfirmService(mock_auth.db, MagicMock())
            result = await service.list()

            assert result["items"] == []
            assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_list_with_status_filter(self, mock_auth, mock_pending_model):
        """测试按状态筛选"""
        with patch("app.plugin.module_modbus.control.services.pending_confirm_service.PendingConfirmCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.list_pending = AsyncMock(return_value=[mock_pending_model])

            service = PendingConfirmService(mock_auth.db, MagicMock())
            result = await service.list(status="pending")

            # 验证筛选参数传递
            mock_crud_instance.list_pending.assert_called_once_with(status="pending")
            assert "items" in result


class TestPendingConfirmServiceConfirm:
    """confirm 方法测试"""

    @pytest.mark.asyncio
    async def test_confirm_not_found(self, mock_auth):
        """测试确认 - 记录不存在"""
        with patch("app.plugin.module_modbus.control.services.pending_confirm_service.PendingConfirmCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.get_by_id = AsyncMock(return_value=None)

            service = PendingConfirmService(mock_auth.db, MagicMock())
            result = await service.confirm(pending_id=999, user_id=1, data=ConfirmAction(comment="确认"))

            assert result["success"] is False
            assert "不存在" in result["message"]

    @pytest.mark.asyncio
    async def test_confirm_already_processed(self, mock_auth, mock_pending_model):
        """测试确认 - 已处理"""
        mock_pending_model.confirm_status = "confirmed"

        with patch("app.plugin.module_modbus.control.services.pending_confirm_service.PendingConfirmCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.get_by_id = AsyncMock(return_value=mock_pending_model)

            service = PendingConfirmService(mock_auth.db, MagicMock())
            result = await service.confirm(pending_id=1, user_id=1, data=ConfirmAction(comment="确认"))

            assert result["success"] is False
            assert "已处理" in result["message"]

    @pytest.mark.asyncio
    async def test_confirm_expired(self, mock_auth, mock_pending_model):
        """测试确认 - 已过期"""
        mock_pending_model.confirm_status = "pending"
        mock_pending_model.expires_at = datetime.now() - timedelta(hours=1)

        with patch("app.plugin.module_modbus.control.services.pending_confirm_service.PendingConfirmCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.get_by_id = AsyncMock(return_value=mock_pending_model)
            mock_crud_instance.mark_expired = AsyncMock()

            service = PendingConfirmService(mock_auth.db, MagicMock())
            result = await service.confirm(pending_id=1, user_id=1, data=ConfirmAction(comment="确认"))

            assert result["success"] is False
            assert "过期" in result["message"]

    @pytest.mark.asyncio
    async def test_confirm_device_not_found(self, mock_auth, mock_pending_model):
        """测试确认 - 设备不存在"""
        mock_pending_model.confirm_status = "pending"
        mock_pending_model.expires_at = None
        mock_pending_model.target_value = 50.0
        mock_pending_model.device_name = "不存在的设备"

        with patch("app.plugin.module_modbus.control.services.pending_confirm_service.PendingConfirmCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.get_by_id = AsyncMock(return_value=mock_pending_model)

            # Mock 数据库查询返回 None
            mock_execute_result = MagicMock()
            mock_execute_result.scalar_one_or_none.return_value = None
            mock_auth.db.execute = AsyncMock(return_value=mock_execute_result)

            service = PendingConfirmService(mock_auth.db, MagicMock())
            result = await service.confirm(pending_id=1, user_id=1, data=ConfirmAction(comment="确认"))

            assert result["success"] is False
            assert "设备" in result["message"]

    @pytest.mark.asyncio
    async def test_confirm_target_value_none(self, mock_auth, mock_pending_model, mock_device_model):
        """测试确认 - 目标值为 None"""
        mock_pending_model.confirm_status = "pending"
        mock_pending_model.expires_at = None
        mock_pending_model.target_value = None
        mock_pending_model.device_name = "测试PLC"

        with patch("app.plugin.module_modbus.control.services.pending_confirm_service.PendingConfirmCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.get_by_id = AsyncMock(return_value=mock_pending_model)

            # Mock 设备查询
            mock_execute_result = MagicMock()
            mock_execute_result.scalar_one_or_none.return_value = mock_device_model
            mock_auth.db.execute = AsyncMock(return_value=mock_execute_result)

            service = PendingConfirmService(mock_auth.db, MagicMock())
            result = await service.confirm(pending_id=1, user_id=1, data=ConfirmAction(comment="确认"))

            assert result["success"] is False
            assert "目标值" in result["message"]


class TestPendingConfirmServiceReject:
    """reject 方法测试"""

    @pytest.mark.asyncio
    async def test_reject_success(self, mock_auth, mock_pending_model):
        """测试拒绝 - 正常"""
        mock_pending_model.confirm_status = "pending"

        with patch("app.plugin.module_modbus.control.services.pending_confirm_service.PendingConfirmCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.get_by_id = AsyncMock(return_value=mock_pending_model)
            mock_crud_instance.reject = AsyncMock()

            service = PendingConfirmService(mock_auth.db, MagicMock())
            result = await service.reject(pending_id=1, user_id=1, data=ConfirmAction(comment="拒绝"))

            assert result["success"] is True
            assert "拒绝" in result["message"]

    @pytest.mark.asyncio
    async def test_reject_not_found(self, mock_auth):
        """测试拒绝 - 不存在"""
        with patch("app.plugin.module_modbus.control.services.pending_confirm_service.PendingConfirmCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.get_by_id = AsyncMock(return_value=None)

            service = PendingConfirmService(mock_auth.db, MagicMock())
            result = await service.reject(pending_id=999, user_id=1, data=ConfirmAction(comment="拒绝"))

            assert result["success"] is False
            assert "不存在" in result["message"]

    @pytest.mark.asyncio
    async def test_reject_already_processed(self, mock_auth, mock_pending_model):
        """测试拒绝 - 已处理"""
        mock_pending_model.confirm_status = "rejected"

        with patch("app.plugin.module_modbus.control.services.pending_confirm_service.PendingConfirmCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.get_by_id = AsyncMock(return_value=mock_pending_model)

            service = PendingConfirmService(mock_auth.db, MagicMock())
            result = await service.reject(pending_id=1, user_id=1, data=ConfirmAction(comment="拒绝"))

            assert result["success"] is False
            assert "已处理" in result["message"]

    @pytest.mark.asyncio
    async def test_reject_with_comment(self, mock_auth, mock_pending_model):
        """测试拒绝 - 带备注"""
        mock_pending_model.confirm_status = "pending"

        with patch("app.plugin.module_modbus.control.services.pending_confirm_service.PendingConfirmCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.get_by_id = AsyncMock(return_value=mock_pending_model)
            mock_crud_instance.reject = AsyncMock()

            service = PendingConfirmService(mock_auth.db, MagicMock())
            result = await service.reject(
                pending_id=1,
                user_id=1,
                data=ConfirmAction(comment="风险过大，不予执行")
            )

            assert result["success"] is True
            # 验证备注被传递
            mock_crud_instance.reject.assert_called_once_with(1, 1, "风险过大，不予执行")
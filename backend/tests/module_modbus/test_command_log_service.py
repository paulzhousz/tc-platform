"""
CommandLogService 单元测试
"""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from app.plugin.module_modbus.control.services.command_log_service import CommandLogService
from app.plugin.module_modbus.schemas import CommandLogFilter


class TestCommandLogServiceList:
    """list 方法测试"""

    @pytest.mark.asyncio
    async def test_list_success(self, mock_auth, mock_log_model):
        """测试获取列表 - 正常"""
        with patch("app.plugin.module_modbus.control.services.command_log_service.CommandLogCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.list_with_filter = AsyncMock(return_value=([mock_log_model], 1))

            service = CommandLogService(mock_auth.db)
            filter_params = CommandLogFilter()
            result = await service.list(filter_params=filter_params, page=1, page_size=20)

            assert "items" in result
            assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_list_empty(self, mock_auth):
        """测试获取列表 - 空列表"""
        with patch("app.plugin.module_modbus.control.services.command_log_service.CommandLogCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.list_with_filter = AsyncMock(return_value=([], 0))

            service = CommandLogService(mock_auth.db)
            filter_params = CommandLogFilter()
            result = await service.list(filter_params=filter_params, page=1, page_size=20)

            assert result["items"] == []
            assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_list_with_device_filter(self, mock_auth, mock_log_model):
        """测试按设备ID筛选"""
        with patch("app.plugin.module_modbus.control.services.command_log_service.CommandLogCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.list_with_filter = AsyncMock(return_value=([mock_log_model], 1))

            service = CommandLogService(mock_auth.db)
            filter_params = CommandLogFilter(device_id=1)
            result = await service.list(filter_params=filter_params, page=1, page_size=20)

            assert "items" in result
            # 验证筛选参数传递
            mock_crud_instance.list_with_filter.assert_called_once()
            call_args = mock_crud_instance.list_with_filter.call_args
            assert call_args.kwargs["filter_params"].device_id == 1

    @pytest.mark.asyncio
    async def test_list_with_user_filter(self, mock_auth, mock_log_model):
        """测试按用户ID筛选"""
        with patch("app.plugin.module_modbus.control.services.command_log_service.CommandLogCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.list_with_filter = AsyncMock(return_value=([mock_log_model], 1))

            service = CommandLogService(mock_auth.db)
            filter_params = CommandLogFilter(user_id=1)
            result = await service.list(filter_params=filter_params, page=1, page_size=20)

            assert "items" in result

    @pytest.mark.asyncio
    async def test_list_with_action_filter(self, mock_auth, mock_log_model):
        """测试按操作类型筛选"""
        with patch("app.plugin.module_modbus.control.services.command_log_service.CommandLogCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.list_with_filter = AsyncMock(return_value=([mock_log_model], 1))

            service = CommandLogService(mock_auth.db)
            filter_params = CommandLogFilter(action="read")
            result = await service.list(filter_params=filter_params, page=1, page_size=20)

            assert "items" in result

    @pytest.mark.asyncio
    async def test_list_with_status_filter(self, mock_auth, mock_log_model):
        """测试按状态筛选"""
        with patch("app.plugin.module_modbus.control.services.command_log_service.CommandLogCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.list_with_filter = AsyncMock(return_value=([mock_log_model], 1))

            service = CommandLogService(mock_auth.db)
            filter_params = CommandLogFilter(status="success")
            result = await service.list(filter_params=filter_params, page=1, page_size=20)

            assert "items" in result

    @pytest.mark.asyncio
    async def test_list_with_time_range_filter(self, mock_auth, mock_log_model):
        """测试按时间范围筛选"""
        with patch("app.plugin.module_modbus.control.services.command_log_service.CommandLogCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.list_with_filter = AsyncMock(return_value=([mock_log_model], 1))

            service = CommandLogService(mock_auth.db)
            filter_params = CommandLogFilter(
                start_time=datetime(2026, 1, 1),
                end_time=datetime(2026, 12, 31)
            )
            result = await service.list(filter_params=filter_params, page=1, page_size=20)

            assert "items" in result

    @pytest.mark.asyncio
    async def test_list_with_combined_filters(self, mock_auth, mock_log_model):
        """测试多条件组合筛选"""
        with patch("app.plugin.module_modbus.control.services.command_log_service.CommandLogCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.list_with_filter = AsyncMock(return_value=([mock_log_model], 1))

            service = CommandLogService(mock_auth.db)
            filter_params = CommandLogFilter(
                device_id=1,
                user_id=1,
                action="read",
                status="success"
            )
            result = await service.list(filter_params=filter_params, page=1, page_size=20)

            assert "items" in result

    @pytest.mark.asyncio
    async def test_list_pagination(self, mock_auth, mock_log_model):
        """测试分页参数"""
        with patch("app.plugin.module_modbus.control.services.command_log_service.CommandLogCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.list_with_filter = AsyncMock(return_value=([mock_log_model], 100))

            service = CommandLogService(mock_auth.db)
            filter_params = CommandLogFilter()
            result = await service.list(filter_params=filter_params, page=2, page_size=10)

            # 验证分页参数传递
            mock_crud_instance.list_with_filter.assert_called_once()
            call_args = mock_crud_instance.list_with_filter.call_args
            assert call_args.kwargs["offset"] == 10  # (page - 1) * page_size
            assert call_args.kwargs["limit"] == 10


class TestCommandLogServiceGetDetail:
    """get_detail 方法测试"""

    @pytest.mark.asyncio
    async def test_get_detail_success(self, mock_auth, mock_log_model):
        """测试获取详情 - 正常"""
        with patch("app.plugin.module_modbus.control.services.command_log_service.CommandLogCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.get_by_id = AsyncMock(return_value=mock_log_model)

            service = CommandLogService(mock_auth.db)
            result = await service.get_detail(id=1)

            assert result is not None
            assert result["action"] == "read"

    @pytest.mark.asyncio
    async def test_get_detail_not_found(self, mock_auth):
        """测试获取详情 - 不存在"""
        with patch("app.plugin.module_modbus.control.services.command_log_service.CommandLogCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.get_by_id = AsyncMock(return_value=None)

            service = CommandLogService(mock_auth.db)
            result = await service.get_detail(id=999)

            assert result is None

    @pytest.mark.asyncio
    async def test_get_detail_model_validation(self, mock_auth, mock_log_model):
        """测试模型验证"""
        with patch("app.plugin.module_modbus.control.services.command_log_service.CommandLogCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.get_by_id = AsyncMock(return_value=mock_log_model)

            service = CommandLogService(mock_auth.db)
            result = await service.get_detail(id=1)

            # 验证返回的是字典而非模型对象
            assert isinstance(result, dict)
            assert "id" in result
            assert "action" in result
            assert "log_status" in result
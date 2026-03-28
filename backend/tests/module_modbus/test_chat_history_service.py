"""
ChatHistoryService 单元测试
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.plugin.module_modbus.control.services.chat_history_service import ChatHistoryService
from app.plugin.module_modbus.schemas import ChatHistoryCreate, ChatMessageItem


class TestChatHistoryServiceList:
    """list 方法测试"""

    @pytest.mark.asyncio
    async def test_list_success(self, mock_auth, mock_chat_history_model):
        """测试获取列表 - 正常"""
        with patch("app.plugin.module_modbus.control.services.chat_history_service.ChatHistoryCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.list_by_user = AsyncMock(return_value=([mock_chat_history_model], 1))

            service = ChatHistoryService(mock_auth.db)
            result = await service.list(user_id=1, page=1, page_size=20)

            assert "items" in result
            assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_list_empty(self, mock_auth):
        """测试获取列表 - 空列表"""
        with patch("app.plugin.module_modbus.control.services.chat_history_service.ChatHistoryCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.list_by_user = AsyncMock(return_value=([], 0))

            service = ChatHistoryService(mock_auth.db)
            result = await service.list(user_id=1, page=1, page_size=20)

            assert result["items"] == []
            assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_list_pagination(self, mock_auth, mock_chat_history_model):
        """测试分页参数"""
        with patch("app.plugin.module_modbus.control.services.chat_history_service.ChatHistoryCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.list_by_user = AsyncMock(return_value=([mock_chat_history_model], 100))

            service = ChatHistoryService(mock_auth.db)
            result = await service.list(user_id=1, page=2, page_size=10)

            # 验证分页参数传递
            mock_crud_instance.list_by_user.assert_called_once()
            call_args = mock_crud_instance.list_by_user.call_args
            assert call_args.kwargs["offset"] == 10  # (page - 1) * page_size
            assert call_args.kwargs["limit"] == 10


class TestChatHistoryServiceGetDetail:
    """get_detail 方法测试"""

    @pytest.mark.asyncio
    async def test_get_detail_success(self, mock_auth, mock_chat_history_model):
        """测试获取详情 - 正常"""
        with patch("app.plugin.module_modbus.control.services.chat_history_service.ChatHistoryCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.get_by_session_id = AsyncMock(return_value=mock_chat_history_model)

            service = ChatHistoryService(mock_auth.db)
            result = await service.get_detail(session_id="session-123", user_id=1)

            assert result is not None
            assert result["session_id"] == "session-123"

    @pytest.mark.asyncio
    async def test_get_detail_not_found(self, mock_auth):
        """测试获取详情 - 不存在"""
        with patch("app.plugin.module_modbus.control.services.chat_history_service.ChatHistoryCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.get_by_session_id = AsyncMock(return_value=None)

            service = ChatHistoryService(mock_auth.db)
            result = await service.get_detail(session_id="not-exist", user_id=1)

            assert result is None

    @pytest.mark.asyncio
    async def test_get_detail_user_mismatch(self, mock_auth, mock_chat_history_model):
        """测试获取详情 - 用户不匹配时返回 None"""
        with patch("app.plugin.module_modbus.control.services.chat_history_service.ChatHistoryCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            # 模拟用户不匹配时返回 None
            mock_crud_instance.get_by_session_id = AsyncMock(return_value=None)

            service = ChatHistoryService(mock_auth.db)
            result = await service.get_detail(session_id="session-123", user_id=999)

            assert result is None


class TestChatHistoryServiceCreate:
    """create 方法测试"""

    @pytest.mark.asyncio
    async def test_create_success(self, mock_auth, mock_chat_history_model):
        """测试创建 - 正常"""
        data = ChatHistoryCreate(
            session_id="new-session",
            messages=[
                ChatMessageItem(role="user", content="读取温度", timestamp="2026-03-25T10:00:00Z")
            ],
            device_count=1,
            device_names=["测试PLC"]
        )

        with patch("app.plugin.module_modbus.control.services.chat_history_service.ChatHistoryCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.create_history = AsyncMock(return_value=mock_chat_history_model)

            service = ChatHistoryService(mock_auth.db)
            result = await service.create(user_id=1, data=data)

            assert result["success"] is True
            assert "session_id" in result

    @pytest.mark.asyncio
    async def test_create_empty_messages(self, mock_auth):
        """测试创建 - 空消息"""
        data = ChatHistoryCreate(
            session_id="new-session",
            messages=[],
            device_count=0,
            device_names=[]
        )

        service = ChatHistoryService(mock_auth.db)
        result = await service.create(user_id=1, data=data)

        assert result["success"] is False
        assert "不能为空" in result["message"]

    @pytest.mark.asyncio
    async def test_create_generates_title(self, mock_auth, mock_chat_history_model):
        """测试创建 - 自动生成标题"""
        data = ChatHistoryCreate(
            session_id="new-session",
            messages=[
                ChatMessageItem(role="user", content="这是一条很长的用户消息用于测试标题截断功能是否正常工作", timestamp="2026-03-25T10:00:00Z")
            ],
            device_count=1,
            device_names=["测试PLC"]
        )

        with patch("app.plugin.module_modbus.control.services.chat_history_service.ChatHistoryCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.create_history = AsyncMock(return_value=mock_chat_history_model)

            service = ChatHistoryService(mock_auth.db)
            await service.create(user_id=1, data=data)

            # 验证标题生成逻辑
            call_args = mock_crud_instance.create_history.call_args
            assert call_args.kwargs["title"] is not None
            assert len(call_args.kwargs["title"]) <= 53  # 50 + "..."


class TestChatHistoryServiceDelete:
    """delete 和 clear_all 方法测试"""

    @pytest.mark.asyncio
    async def test_delete_success(self, mock_auth):
        """测试删除 - 正常"""
        with patch("app.plugin.module_modbus.control.services.chat_history_service.ChatHistoryCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.delete_by_session_id = AsyncMock(return_value=True)

            service = ChatHistoryService(mock_auth.db)
            result = await service.delete(session_id="session-123", user_id=1)

            assert result["success"] is True
            assert "删除" in result["message"]

    @pytest.mark.asyncio
    async def test_delete_not_found(self, mock_auth):
        """测试删除 - 不存在"""
        with patch("app.plugin.module_modbus.control.services.chat_history_service.ChatHistoryCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.delete_by_session_id = AsyncMock(return_value=False)

            service = ChatHistoryService(mock_auth.db)
            result = await service.delete(session_id="not-exist", user_id=1)

            assert result["success"] is False
            assert "不存在" in result["message"]

    @pytest.mark.asyncio
    async def test_clear_all(self, mock_auth):
        """测试清空所有"""
        with patch("app.plugin.module_modbus.control.services.chat_history_service.ChatHistoryCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.delete_all_by_user = AsyncMock(return_value=5)

            service = ChatHistoryService(mock_auth.db)
            result = await service.clear_all(user_id=1)

            assert result["success"] is True
            assert "5" in result["message"]

    @pytest.mark.asyncio
    async def test_clear_all_empty(self, mock_auth):
        """测试清空所有 - 无记录"""
        with patch("app.plugin.module_modbus.control.services.chat_history_service.ChatHistoryCRUD") as mock_crud:
            mock_crud_instance = mock_crud.return_value
            mock_crud_instance.delete_all_by_user = AsyncMock(return_value=0)

            service = ChatHistoryService(mock_auth.db)
            result = await service.clear_all(user_id=1)

            assert result["success"] is True
            assert "0" in result["message"]


class TestChatHistoryServiceTimestamp:
    """_parse_timestamp 方法测试"""

    def test_parse_timestamp_with_z(self, mock_auth):
        """测试解析 Z 结尾的时间戳"""
        service = ChatHistoryService(mock_auth.db)
        result = service._parse_timestamp("2026-03-25T10:00:00Z")
        assert result is not None

    def test_parse_timestamp_with_timezone(self, mock_auth):
        """测试解析带时区的时间戳"""
        service = ChatHistoryService(mock_auth.db)
        result = service._parse_timestamp("2026-03-25T10:00:00+08:00")
        assert result is not None

    def test_parse_timestamp_empty(self, mock_auth):
        """测试空时间戳"""
        service = ChatHistoryService(mock_auth.db)
        result = service._parse_timestamp("")
        assert result is not None

    def test_parse_timestamp_invalid(self, mock_auth):
        """测试无效时间戳"""
        service = ChatHistoryService(mock_auth.db)
        result = service._parse_timestamp("invalid")
        assert result is not None
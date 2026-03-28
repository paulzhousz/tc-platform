"""
聊天历史业务逻辑层
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.plugin.module_modbus.control.crud.chat_history import ChatHistoryCRUD
from app.plugin.module_modbus.schemas import (
    ChatHistoryCreate,
    ChatHistoryDetailResponse,
    ChatHistoryListResponse,
    ChatHistoryResponse,
)


class ChatHistoryService:
    """聊天历史业务逻辑层"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._crud = ChatHistoryCRUD(db)

    async def list(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """获取用户聊天历史列表

        参数:
            user_id: 用户ID
            page: 页码
            page_size: 每页数量

        返回:
            分页结果字典
        """
        offset = (page - 1) * page_size
        histories, total = await self._crud.list_by_user(
            user_id=user_id,
            offset=offset,
            limit=page_size,
        )
        items = [ChatHistoryResponse.model_validate(h) for h in histories]
        return ChatHistoryListResponse(items=items, total=total).model_dump()

    async def get_detail(self, session_id: str, user_id: int) -> dict[str, Any] | None:
        """获取聊天历史详情

        参数:
            session_id: 会话ID
            user_id: 用户ID

        返回:
            聊天历史详情字典，不存在则返回 None
        """
        history = await self._crud.get_by_session_id(session_id, user_id)
        if not history:
            return None
        return ChatHistoryDetailResponse.model_validate(history).model_dump()

    async def create(self, user_id: int, data: ChatHistoryCreate) -> dict[str, Any]:
        """保存聊天历史

        参数:
            user_id: 用户ID
            data: 聊天历史创建数据

        返回:
            创建结果
        """
        if not data.messages:
            return {"success": False, "message": "消息列表不能为空"}

        # 生成标题（取第一条用户消息）
        title = None
        for msg in data.messages:
            if msg.role == "user":
                title = msg.content[:50] + ("..." if len(msg.content) > 50 else "")
                break

        # 解析时间戳
        start_time = self._parse_timestamp(data.messages[0].timestamp) if data.messages else datetime.now()
        end_time = self._parse_timestamp(data.messages[-1].timestamp) if data.messages else datetime.now()

        history = await self._crud.create_history(
            user_id=user_id,
            data=data,
            title=title,
            start_time=start_time,
            end_time=end_time,
        )
        return {"success": True, "id": history.id, "session_id": history.session_id}

    async def delete(self, session_id: str, user_id: int) -> dict[str, Any]:
        """删除聊天历史

        参数:
            session_id: 会话ID
            user_id: 用户ID

        返回:
            删除结果
        """
        success = await self._crud.delete_by_session_id(session_id, user_id)
        if success:
            return {"success": True, "message": "聊天历史已删除"}
        return {"success": False, "message": "聊天历史不存在"}

    async def clear_all(self, user_id: int) -> dict[str, Any]:
        """清空用户所有聊天历史

        参数:
            user_id: 用户ID

        返回:
            清空结果
        """
        count = await self._crud.delete_all_by_user(user_id)
        return {"success": True, "message": f"已清空 {count} 条聊天历史"}

    def _parse_timestamp(self, ts: str) -> datetime:
        """解析 ISO 时间戳

        参数:
            ts: ISO 格式时间戳字符串

        返回:
            datetime 对象（无时区，适配数据库 TIMESTAMP WITHOUT TIME ZONE）
        """
        if not ts:
            return datetime.now()
        try:
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            dt = datetime.fromisoformat(ts)
            # 移除时区信息，适配数据库 TIMESTAMP WITHOUT TIME ZONE
            return dt.replace(tzinfo=None)
        except Exception:
            return datetime.now()

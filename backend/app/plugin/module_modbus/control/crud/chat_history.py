"""
聊天历史 CRUD 层

使用独立的数据访问类。
"""
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import ChatHistoryModel
from ...schemas import ChatHistoryCreate


class ChatHistoryCRUD:
    """聊天历史数据访问层"""

    def __init__(self, db: AsyncSession) -> None:
        """
        初始化聊天历史 CRUD

        参数:
        - db (AsyncSession): 数据库会话
        """
        self.db = db

    async def get_by_id(self, id: int) -> ChatHistoryModel | None:
        """获取聊天历史详情"""
        stmt = select(ChatHistoryModel).where(ChatHistoryModel.id == id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_by_session_id(
        self,
        session_id: str,
        user_id: int,
    ) -> ChatHistoryModel | None:
        """根据会话ID获取聊天历史"""
        stmt = select(ChatHistoryModel).where(
            ChatHistoryModel.session_id == session_id,
            ChatHistoryModel.user_id == user_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_by_user(
        self,
        user_id: int,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[ChatHistoryModel], int]:
        """
        获取用户的聊天历史列表

        参数:
        - user_id: 用户ID
        - offset: 偏移量
        - limit: 每页数量

        返回:
        - tuple[list[ChatHistoryModel], int]: (历史列表, 总数)
        """
        stmt = select(ChatHistoryModel).where(ChatHistoryModel.user_id == user_id)

        # 统计总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # 分页查询
        stmt = stmt.order_by(ChatHistoryModel.created_time.desc()).offset(offset).limit(limit)
        histories = (await self.db.execute(stmt)).scalars().all()

        return histories, total

    async def create_history(
        self,
        user_id: int,
        data: ChatHistoryCreate,
        title: str | None = None,
        start_time=None,
        end_time=None,
    ) -> ChatHistoryModel:
        """创建聊天历史"""
        messages_data = [msg.model_dump() for msg in data.messages]

        history = ChatHistoryModel(
            user_id=user_id,
            session_id=data.session_id,
            title=title,
            messages=messages_data,
            device_count=data.device_count,
            device_names=data.device_names,
            start_time=start_time,
            end_time=end_time,
        )

        self.db.add(history)
        await self.db.flush()
        await self.db.refresh(history)
        return history

    async def delete_by_session_id(
        self,
        session_id: str,
        user_id: int,
    ) -> bool:
        """
        删除指定会话的聊天历史

        返回:
        - bool: 是否成功删除
        """
        stmt = select(ChatHistoryModel).where(
            ChatHistoryModel.session_id == session_id,
            ChatHistoryModel.user_id == user_id,
        )
        history = (await self.db.execute(stmt)).scalar_one_or_none()

        if not history:
            return False

        await self.db.delete(history)
        await self.db.flush()
        return True

    async def delete_all_by_user(self, user_id: int) -> int:
        """
        删除用户的所有聊天历史

        返回:
        - int: 删除的记录数
        """
        stmt = delete(ChatHistoryModel).where(ChatHistoryModel.user_id == user_id)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount

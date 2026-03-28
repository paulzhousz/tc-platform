"""
待确认操作 CRUD 层

使用独立的数据访问类。
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import PendingConfirmModel


class PendingConfirmCRUD:
    """待确认操作数据访问层"""

    def __init__(self, db: AsyncSession) -> None:
        """
        初始化待确认操作 CRUD

        参数:
        - db (AsyncSession): 数据库会话
        """
        self.db = db

    async def get_by_id(self, id: int) -> PendingConfirmModel | None:
        """获取待确认操作详情"""
        stmt = select(PendingConfirmModel).where(PendingConfirmModel.id == id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_pending(
        self,
        status: str | None = None,
    ) -> Sequence[PendingConfirmModel]:
        """
        获取待确认操作列表

        参数:
        - status: 状态筛选

        返回:
        - Sequence[PendingConfirmModel]: 待确认操作列表
        """
        stmt = select(PendingConfirmModel)

        if status:
            stmt = stmt.where(PendingConfirmModel.confirm_status == status)
        else:
            stmt = stmt.where(PendingConfirmModel.confirm_status == "pending")

        stmt = stmt.order_by(PendingConfirmModel.created_time.desc())
        return (await self.db.execute(stmt)).scalars().all()

    async def create_pending(
        self,
        user_id: int | None,
        device_name: str | None,
        tag_name: str | None,
        target_value: float | None,
        unit: str | None = None,
        command_log_id: int | None = None,
        user_input: str | None = None,
        ai_explanation: str | None = None,
        expires_at: datetime | None = None,
    ) -> PendingConfirmModel:
        """创建待确认操作"""
        pending = PendingConfirmModel(
            user_id=user_id,
            command_log_id=command_log_id,
            device_name=device_name,
            tag_name=tag_name,
            target_value=target_value,
            unit=unit,
            user_input=user_input,
            ai_explanation=ai_explanation,
            expires_at=expires_at,
            confirm_status="pending",
        )
        self.db.add(pending)
        await self.db.flush()
        await self.db.refresh(pending)
        return pending

    async def confirm(
        self,
        pending_id: int,
        reviewed_by: int,
        comment: str | None = None,
    ) -> PendingConfirmModel | None:
        """确认操作"""
        pending = await self.get_by_id(pending_id)
        if not pending:
            return None

        pending.confirm_status = "confirmed"
        pending.reviewed_by = reviewed_by
        pending.reviewed_at = datetime.utcnow()
        pending.review_comment = comment

        await self.db.flush()
        await self.db.refresh(pending)
        return pending

    async def reject(
        self,
        pending_id: int,
        reviewed_by: int,
        comment: str | None = None,
    ) -> PendingConfirmModel | None:
        """拒绝操作"""
        pending = await self.get_by_id(pending_id)
        if not pending:
            return None

        pending.confirm_status = "rejected"
        pending.reviewed_by = reviewed_by
        pending.reviewed_at = datetime.utcnow()
        pending.review_comment = comment

        await self.db.flush()
        await self.db.refresh(pending)
        return pending

    async def mark_expired(self, pending_id: int) -> PendingConfirmModel | None:
        """标记为过期"""
        pending = await self.get_by_id(pending_id)
        if not pending:
            return None

        pending.confirm_status = "expired"
        await self.db.flush()
        await self.db.refresh(pending)
        return pending

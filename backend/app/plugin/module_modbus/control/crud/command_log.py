"""
命令日志 CRUD 层

由于命令日志不需要标准的 Create/Update Schema，
使用独立的数据访问类而非继承 CRUDBase。
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models import CommandLogModel
from ...schemas import CommandLogFilter


class CommandLogCRUD:
    """命令日志数据访问层"""

    def __init__(self, db: AsyncSession) -> None:
        """
        初始化命令日志 CRUD

        参数:
        - db (AsyncSession): 数据库会话
        """
        self.db = db

    async def get_by_id(self, id: int) -> CommandLogModel | None:
        """获取日志详情"""
        stmt = select(CommandLogModel).where(CommandLogModel.id == id)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_with_filter(
        self,
        filter_params: CommandLogFilter,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[CommandLogModel], int]:
        """
        带筛选条件的分页查询

        参数:
        - filter_params: 筛选参数
        - offset: 偏移量
        - limit: 每页数量

        返回:
        - tuple[list[CommandLogModel], int]: (日志列表, 总数)
        """
        stmt = select(CommandLogModel)

        if filter_params.device_id:
            stmt = stmt.where(CommandLogModel.device_id == filter_params.device_id)
        if filter_params.user_id:
            stmt = stmt.where(CommandLogModel.user_id == filter_params.user_id)
        if filter_params.action:
            stmt = stmt.where(CommandLogModel.action == filter_params.action)
        if filter_params.status:
            stmt = stmt.where(CommandLogModel.log_status == filter_params.status)
        if filter_params.start_time:
            stmt = stmt.where(CommandLogModel.created_time >= filter_params.start_time)
        if filter_params.end_time:
            stmt = stmt.where(CommandLogModel.created_time <= filter_params.end_time)

        # 统计总数
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # 分页查询
        stmt = stmt.order_by(CommandLogModel.created_time.desc()).offset(offset).limit(limit)
        logs = (await self.db.execute(stmt)).scalars().all()

        return logs, total

    async def create_log(
        self,
        user_id: int,
        action: str,
        device_id: int | None = None,
        tag_id: int | None = None,
        session_id: str | None = None,
        request_value: float | None = None,
        user_input: str | None = None,
        ai_reasoning: str | None = None,
    ) -> CommandLogModel:
        """创建操作日志"""
        log = CommandLogModel(
            user_id=user_id,
            action=action,
            device_id=device_id,
            tag_id=tag_id,
            session_id=session_id,
            request_value=request_value,
            user_input=user_input,
            ai_reasoning=ai_reasoning,
            log_status="pending",
        )
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log

    async def update_log_status(
        self,
        log_id: int,
        status: str,
        actual_value: float | None = None,
        error_message: str | None = None,
        execution_time: float | None = None,
    ) -> CommandLogModel | None:
        """更新日志状态"""
        log = await self.get_by_id(log_id)
        if not log:
            return None

        log.log_status = status
        if actual_value is not None:
            log.actual_value = actual_value
        if error_message:
            log.error_message = error_message
        if execution_time is not None:
            log.execution_time = execution_time
        log.executed_at = datetime.utcnow()

        await self.db.flush()
        await self.db.refresh(log)
        return log

"""
命令日志业务逻辑层
"""
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.plugin.module_modbus.control.crud.command_log import CommandLogCRUD
from app.plugin.module_modbus.schemas import (
    CommandLogFilter,
    CommandLogListResponse,
    CommandLogResponse,
)


class CommandLogService:
    """命令日志业务逻辑层"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._crud = CommandLogCRUD(db)

    async def list(
        self,
        filter_params: CommandLogFilter,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """获取操作日志列表

        参数:
            filter_params: 筛选参数
            page: 页码
            page_size: 每页数量

        返回:
            分页结果字典
        """
        offset = (page - 1) * page_size
        logs, total = await self._crud.list_with_filter(
            filter_params=filter_params,
            offset=offset,
            limit=page_size,
        )
        items = [CommandLogResponse.model_validate(log) for log in logs]
        return CommandLogListResponse(items=items, total=total).model_dump()

    async def get_detail(self, id: int) -> dict[str, Any] | None:
        """获取操作日志详情

        参数:
            id: 日志ID

        返回:
            日志详情字典，不存在则返回 None
        """
        log = await self._crud.get_by_id(id)
        if not log:
            return None
        return CommandLogResponse.model_validate(log).model_dump()

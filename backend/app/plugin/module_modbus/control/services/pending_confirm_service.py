"""
待确认操作业务逻辑层
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from redis.asyncio.client import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.plugin.module_modbus.control.crud.pending_confirm import PendingConfirmCRUD
from app.plugin.module_modbus.control.services.plc_service import PLCService
from app.plugin.module_modbus.models import DeviceModel, TagPointModel
from app.plugin.module_modbus.schemas import (
    ConfirmAction,
    PendingConfirmListResponse,
    PendingConfirmResponse,
)


class PendingConfirmService:
    """待确认操作业务逻辑层"""

    def __init__(self, db: AsyncSession, redis: Redis | None = None):
        self.db = db
        self._redis = redis
        self._crud = PendingConfirmCRUD(db)

    async def list(self, status: str | None = None) -> dict[str, Any]:
        """获取待确认操作列表

        参数:
            status: 状态筛选

        返回:
            列表结果字典
        """
        pendings = await self._crud.list_pending(status=status)
        items = [PendingConfirmResponse.model_validate(p) for p in pendings]
        return PendingConfirmListResponse(items=items, total=len(items)).model_dump()

    async def confirm(
        self,
        pending_id: int,
        user_id: int,
        data: ConfirmAction,
    ) -> dict[str, Any]:
        """确认操作

        参数:
            pending_id: 待确认ID
            user_id: 用户ID
            data: 确认数据

        返回:
            操作结果
        """
        pending = await self._crud.get_by_id(pending_id)
        if not pending:
            return {"success": False, "message": "待确认记录不存在"}

        if pending.confirm_status != "pending":
            return {"success": False, "message": f"该操作已处理，状态: {pending.confirm_status}"}

        # 检查是否过期
        if pending.expires_at and datetime.now() > pending.expires_at:
            await self._crud.mark_expired(pending_id)
            return {"success": False, "message": "操作已过期"}

        # 获取设备和点位
        stmt = select(DeviceModel).where(DeviceModel.name == pending.device_name)
        device = (await self.db.execute(stmt)).scalar_one_or_none()
        if not device:
            return {"success": False, "message": f"设备 '{pending.device_name}' 不存在"}

        stmt = select(TagPointModel).where(
            TagPointModel.device_id == device.id,
            TagPointModel.name == pending.tag_name,
        )
        tag = (await self.db.execute(stmt)).scalar_one_or_none()
        if not tag:
            return {"success": False, "message": f"点位 '{pending.tag_name}' 不存在"}

        # 检查目标值是否存在
        if pending.target_value is None:
            return {"success": False, "message": "目标值不存在"}

        # 执行写入操作
        plc_service = PLCService(self.db, self._redis)
        result = await plc_service.write(
            device_id=device.id,
            tag_code=tag.code,
            value=pending.target_value,
            user_id=user_id,
        )

        # 更新状态
        await self._crud.confirm(pending_id, user_id, data.comment)

        if result["success"]:
            return {
                "success": True,
                "message": "操作已确认并执行",
                "result": result,
            }
        return {"success": False, "message": f"执行失败: {result['message']}"}

    async def reject(
        self,
        pending_id: int,
        user_id: int,
        data: ConfirmAction,
    ) -> dict[str, Any]:
        """拒绝操作

        参数:
            pending_id: 待确认ID
            user_id: 用户ID
            data: 拒绝数据

        返回:
            操作结果
        """
        pending = await self._crud.get_by_id(pending_id)
        if not pending:
            return {"success": False, "message": "待确认记录不存在"}

        if pending.confirm_status != "pending":
            return {"success": False, "message": f"该操作已处理，状态: {pending.confirm_status}"}

        await self._crud.reject(pending_id, user_id, data.comment)
        return {"success": True, "message": "操作已拒绝"}

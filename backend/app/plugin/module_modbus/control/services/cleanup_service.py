"""
日志清理服务

定期清理过期日志、待确认记录和 Agent 会话。
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.setting import settings
from app.plugin.module_modbus.models import (
    AgentSessionModel,
    CommandLogModel,
    PendingConfirmModel,
)

logger = logging.getLogger(__name__)


class LogCleanupService:
    """日志清理服务

    功能：
    - 定期清理过期日志
    - 清理过期待确认记录
    - 清理过期会话记录
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._retention_days = settings.MODBUS_LOG_RETENTION_DAYS
        self._pending_expire_minutes = settings.MODBUS_PENDING_EXPIRE_MINUTES

    async def cleanup_command_logs(self) -> int:
        """清理过期的操作日志

        Returns:
            清理的记录数
        """
        cutoff = datetime.now() - timedelta(days=self._retention_days)

        stmt = delete(CommandLogModel).where(CommandLogModel.created_time < cutoff)
        result = await self.db.execute(stmt)
        await self.db.commit()

        deleted = result.rowcount
        if deleted > 0:
            logger.info(
                f"清理了 {deleted} 条过期操作日志（保留 {self._retention_days} 天）"
            )

        return deleted

    async def cleanup_pending_confirms(self) -> int:
        """清理过期的待确认记录

        Returns:
            清理/更新的记录数
        """
        from app.plugin.module_modbus.control.services.websocket_service import (
            ws_manager,
        )

        now = datetime.now()

        # 查询过期的 pending 记录
        stmt = select(PendingConfirmModel).where(
            PendingConfirmModel.status == "pending",
            PendingConfirmModel.expires_at < now,
        )
        expired = (await self.db.execute(stmt)).scalars().all()

        count = 0
        for pending in expired:
            pending.status = "expired"
            count += 1

            # 发送过期通知
            try:
                asyncio.create_task(
                    ws_manager.send_to_user(
                        pending.user_id,
                        {
                            "type": "pending_expired",
                            "data": {
                                "pending_confirm_id": pending.id,
                                "device_name": pending.device_name,
                                "tag_name": pending.tag_name,
                                "target_value": pending.target_value,
                                "message": "操作已过期，未在规定时间内确认",
                            },
                        },
                    )
                )
            except Exception as e:
                logger.error(f"发送过期通知失败: {e}")

        await self.db.commit()

        if count > 0:
            logger.info(f"标记了 {count} 条待确认记录为过期")

        return count

    async def cleanup_agent_sessions(self) -> int:
        """清理过期的 Agent 会话

        Returns:
            清理的记录数
        """
        cutoff = datetime.now() - timedelta(
            minutes=settings.MODBUS_LLM_SESSION_TTL_MINUTES
        )

        stmt = delete(AgentSessionModel).where(
            AgentSessionModel.last_active < cutoff
        )
        result = await self.db.execute(stmt)
        await self.db.commit()

        deleted = result.rowcount
        if deleted > 0:
            logger.info(f"清理了 {deleted} 条过期 Agent 会话")

        return deleted

    async def cleanup_all(self) -> dict[str, Any]:
        """执行所有清理任务

        Returns:
            各类清理的统计
        """
        result = {
            "command_logs": await self.cleanup_command_logs(),
            "pending_confirms": await self.cleanup_pending_confirms(),
            "agent_sessions": await self.cleanup_agent_sessions(),
        }

        return result


async def cleanup_expired_data(db: AsyncSession) -> dict[str, Any]:
    """清理过期数据的便捷函数

    Args:
        db: 数据库会话

    Returns:
        清理统计
    """
    service = LogCleanupService(db)
    return await service.cleanup_all()
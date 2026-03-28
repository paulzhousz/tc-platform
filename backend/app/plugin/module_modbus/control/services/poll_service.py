"""
设备状态轮询服务

定期轮询设备在线状态，检测点位值变化并推送通知。
"""

import asyncio
import logging
from datetime import datetime

from redis.asyncio.client import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.plugin.module_modbus.control.services.config_service import ModbusConfigService
from app.plugin.module_modbus.control.services.connection_pool import connection_pool
from app.plugin.module_modbus.control.services.websocket_service import ws_manager
from app.plugin.module_modbus.models import DeviceModel, TagPointModel

logger = logging.getLogger(__name__)


class PollService:
    """设备状态轮询服务

    功能：
    - 定期轮询设备在线状态
    - 检测点位值变化并推送
    - 离线检测和通知
    """

    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None
        self._redis: Redis | None = None
        # 设备上次在线状态 {device_id: bool}
        self._device_status: dict[int, bool] = {}
        # 点位上次值 {tag_id: float}
        self._tag_values: dict[int, float] = {}
        # 设备最后通信时间 {device_id: datetime}
        self._last_seen: dict[int, datetime] = {}
        # 离线阈值（秒）
        self._offline_threshold: int = 0

    async def start(self, redis: Redis):
        """启动轮询服务

        参数:
            redis: Redis 客户端实例
        """
        if self._running:
            logger.warning("轮询服务已在运行中")
            return

        self._redis = redis
        self._offline_threshold = await ModbusConfigService.get(redis, "modbus_poll_interval") * 3
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("设备状态轮询服务已启动")

    def stop(self):
        """停止轮询服务"""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        # 清除缓存状态
        self._device_status.clear()
        self._tag_values.clear()
        self._last_seen.clear()
        logger.info("设备状态轮询服务已停止")

    async def _poll_loop(self):
        """轮询主循环"""
        while self._running:
            try:
                await self._poll_all_devices()
            except Exception as e:
                logger.error(f"轮询设备状态失败: {e}")

            # 等待下一轮
            if self._redis:
                interval = await ModbusConfigService.get(self._redis, "modbus_poll_interval")
                await asyncio.sleep(interval)
            else:
                await asyncio.sleep(5)  # 默认值

    async def _poll_all_devices(self):
        """轮询所有在线设备"""
        # 使用 async session factory
        from app.core.database import async_db_session

        async with async_db_session() as db:
            try:
                # 只获取在线且启用的设备
                stmt = select(DeviceModel).where(
                    DeviceModel.is_active == True,
                    DeviceModel.device_status == "online",
                )
                devices = (await db.execute(stmt)).scalars().all()

                for device in devices:
                    try:
                        await self._poll_device(db, device)
                    except Exception as e:
                        logger.error(f"轮询设备 {device.name} 失败: {e}")

                # 检查离线设备
                await self._check_offline_devices(db)

            except Exception as e:
                logger.error(f"轮询设备失败: {e}")

    async def _poll_device(self, db: AsyncSession, device: DeviceModel):
        """轮询单个设备"""
        # 尝试读取设备的一个寄存器来检测连接状态
        stmt = select(TagPointModel).where(
            TagPointModel.device_id == device.id, TagPointModel.is_active == True
        )
        # 设备可能有多个点位，只需取第一个用于检测连接状态
        tag = (await db.execute(stmt)).scalars().first()

        if not tag:
            # 没有点位，只检查连接
            is_online = await self._check_connection(device)
            await self._update_device_status(db, device, is_online)
            return

        # 读取点位值
        try:
            result = await self._read_tag_value(device, tag)
            if result is not None:
                is_online = True
                self._last_seen[device.id] = datetime.now()

                # 检查值变化
                await self._check_value_change(db, device, tag, result)

            else:
                is_online = False

            await self._update_device_status(db, device, is_online)

        except Exception as e:
            logger.debug(f"读取设备 {device.name} 点位 {tag.name} 失败: {e}")
            is_online = False
            await self._update_device_status(db, device, is_online)

    async def _check_connection(self, device: DeviceModel) -> bool:
        """检查设备连接状态"""
        client = connection_pool.acquire(device.id)
        if not client:
            return False

        try:
            # 尝试读取保持寄存器地址 0
            result = client.read_holding_registers(0, 1, slave=device.slave_id)
            return result.get("success", False)
        except Exception:
            return False
        finally:
            connection_pool.release(device.id, client)

    def _normalize_address(self, address: int, register_type: str) -> int:
        """将 PLC 编程地址转换为 Modbus 协议地址

        PLC 编程地址格式：
        - 保持寄存器: 40001-49999 → 地址 0-9999
        - 输入寄存器: 30001-39999 → 地址 0-9999
        - 线圈: 1-9999 → 地址 0-9998
        - 离散输入: 1-9999 → 地址 0-9998
        """
        if register_type == "holding" and address >= 40001:
            return address - 40001
        elif register_type == "input" and address >= 30001:
            return address - 30001
        elif register_type == "coil" and address >= 1:
            return address - 1
        elif register_type == "discrete" and address >= 1:
            return address - 1
        return address

    async def _read_tag_value(
        self, device: DeviceModel, tag: TagPointModel
    ) -> float | None:
        """读取点位值"""
        client = connection_pool.acquire(device.id)
        if not client:
            return None

        try:
            # 根据数据类型确定寄存器数量
            register_count = 1
            if tag.data_type in ["INT32", "UINT32", "FLOAT"]:
                register_count = 2

            # 转换地址
            address = self._normalize_address(tag.address, tag.register_type)

            if tag.register_type == "holding":
                result = client.read_holding_registers(
                    address, register_count, slave=device.slave_id
                )
            elif tag.register_type == "input":
                result = client.read_input_registers(
                    address, register_count, slave=device.slave_id
                )
            elif tag.register_type == "coil":
                result = client.read_coils(
                    address, register_count, slave=device.slave_id
                )
            else:
                return None

            if not result.get("success"):
                return None

            # 应用转换
            if tag.register_type in ["holding", "input"]:
                value = result["values"][0]
                # 应用缩放和偏移: 工程值 = 原始值 * scale_factor + offset
                value = value * tag.scale_factor + tag.offset
            else:  # coil
                value = float(result["values"][0])

            return value

        except Exception as e:
            logger.debug(f"读取点位值失败: {e}")
            return None
        finally:
            connection_pool.release(device.id, client)

    async def _check_value_change(
        self,
        db: AsyncSession,
        device: DeviceModel,
        tag: TagPointModel,
        new_value: float,
    ):
        """检查值变化并推送"""
        old_value = self._tag_values.get(tag.id)

        # 更新缓存
        self._tag_values[tag.id] = new_value

        # 检查是否需要推送
        if old_value is None:
            # 首次读取，不推送
            return

        # 值发生变化，推送通知
        if new_value != old_value:
            # 广播给所有用户
            await ws_manager.send_tag_value(
                user_id=0,  # 广播
                device_id=device.id,
                tag_id=tag.id,
                tag_name=tag.name,
                value=new_value,
                unit=tag.unit,
                previous_value=old_value,
            )
            logger.debug(
                f"点位值变化: {device.name}.{tag.name} " f"{old_value} -> {new_value}"
            )

    async def _update_device_status(
        self, db: AsyncSession, device: DeviceModel, is_online: bool
    ):
        """更新设备状态"""
        old_status = self._device_status.get(device.id)

        # 更新缓存
        self._device_status[device.id] = is_online

        # 状态变化或首次检测时更新数据库并推送
        status = "online" if is_online else "offline"
        should_update = old_status is None or old_status != is_online

        if should_update:
            device.device_status = status
            if is_online:
                device.last_seen = datetime.now()
            await db.commit()

            # 推送状态变化
            await ws_manager.send_device_status(
                device_id=device.id,
                device_name=device.name,
                status=status,
                last_seen=device.last_seen,
            )
            logger.info(f"设备 {device.name} 状态更新: {status}")

    async def _check_offline_devices(self, db: AsyncSession):
        """检查离线设备"""
        now = datetime.now()
        for device_id, last_seen in list(self._last_seen.items()):
            if last_seen:
                elapsed = (now - last_seen).total_seconds()
                if elapsed > self._offline_threshold:
                    # 设备超时离线
                    if self._device_status.get(device_id, True):
                        stmt = select(DeviceModel).where(DeviceModel.id == device_id)
                        device = (await db.execute(stmt)).scalar_one_or_none()
                        if device:
                            await self._update_device_status(db, device, False)

    def get_device_status(self, device_id: int) -> bool | None:
        """获取设备在线状态"""
        return self._device_status.get(device_id)

    def get_tag_value(self, tag_id: int) -> float | None:
        """获取点位当前值"""
        return self._tag_values.get(tag_id)

    def get_all_device_status(self) -> dict[int, bool]:
        """获取所有设备状态"""
        return self._device_status.copy()


# 全局轮询服务实例
poll_service = PollService()

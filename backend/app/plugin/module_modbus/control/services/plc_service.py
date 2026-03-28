"""
PLC 操作服务层

提供 PLC 设备的读写操作，协议无关的业务逻辑层。
支持异步数据库操作。
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any

from redis.asyncio.client import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.plugin.module_modbus.control.services.config_service import ModbusConfigService
from app.plugin.module_modbus.control.services.connection_pool import connection_pool
from app.plugin.module_modbus.models import (
    CommandLogModel,
    DeviceModel,
    PendingConfirmModel,
    TagPointModel,
)

logger = logging.getLogger(__name__)


class PLCService:
    """PLC 操作服务 - 协议无关的业务逻辑层"""

    def __init__(self, db: AsyncSession, redis: Redis | None = None):
        self.db = db
        self._redis = redis

    def _normalize_address(self, address: int, register_type: str) -> int:
        """
        将 PLC 编程地址转换为 Modbus 协议地址

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

    async def read(
        self, device_id: int, tag_code: str, user_id: int | None = None
    ) -> dict[str, Any]:
        """
        读取 PLC 点位值

        Args:
            device_id: 设备 ID
            tag_code: 点位编码
            user_id: 用户 ID（用于日志）

        Returns:
            {"success": bool, "value": float, "raw_value": int, "unit": str, "message": str}
        """
        # 1. 获取点位元数据
        tag_meta = await self._get_tag_meta(device_id, tag_code)
        if not tag_meta:
            return {"success": False, "message": f"未找到点位: {device_id}/{tag_code}"}

        device = tag_meta.device

        # 2. 记录操作日志
        command_log = CommandLogModel(
            user_id=user_id,
            device_id=device_id,
            tag_id=tag_meta.id,
            action="READ",
            log_status="pending",
        )
        self.db.add(command_log)
        await self.db.flush()

        start_time = time.time()

        # 3. 获取连接
        client = connection_pool.acquire(device_id)
        if not client:
            command_log.log_status = "failed"
            command_log.error_message = "无法获取设备连接"
            await self.db.flush()
            return {"success": False, "message": "无法获取设备连接"}

        try:
            # 4. 读取寄存器
            address = self._normalize_address(tag_meta.address, tag_meta.register_type)
            slave_id = device.slave_id

            if tag_meta.register_type == "holding":
                result = client.read_holding_registers(address, 1, slave=slave_id)
            elif tag_meta.register_type == "input":
                result = client.read_input_registers(address, 1, slave=slave_id)
            elif tag_meta.register_type == "coil":
                result = client.read_coils(address, 1, slave=slave_id)
            elif tag_meta.register_type == "discrete":
                result = client.read_discrete_inputs(address, 1, slave=slave_id)
            else:
                return {
                    "success": False,
                    "message": f"不支持的寄存器类型: {tag_meta.register_type}",
                }

            if not result.get("success"):
                command_log.log_status = "failed"
                command_log.error_message = result.get("error", "读取失败")
                await self.db.flush()
                return {"success": False, "message": result.get("error", "读取失败")}

            # 5. 数值转换
            if tag_meta.register_type in ["coil", "discrete"]:
                raw_value = 1 if result["values"][0] else 0
                value = float(raw_value)
            else:
                raw_value = result["values"][0]
                value = self._convert_raw_to_engineering(raw_value, tag_meta)

            # 6. 更新缓存
            tag_meta.current_value = value
            tag_meta.last_updated = datetime.now()

            # 7. 更新日志
            command_log.log_status = "success"
            command_log.actual_value = value
            command_log.execution_time = (time.time() - start_time) * 1000
            command_log.executed_at = datetime.now()
            await self.db.flush()

            return {
                "success": True,
                "value": value,
                "raw_value": raw_value,
                "unit": tag_meta.unit,
                "message": f"当前值: {value} {tag_meta.unit or ''}",
                # 结构化数据
                "device_id": device.id,
                "device_name": device.name,
                "tag_id": tag_meta.id,
                "tag_name": tag_meta.name,
                "min_value": tag_meta.min_value,
                "max_value": tag_meta.max_value,
                "execution_time_ms": int((time.time() - start_time) * 1000),
                "command_log_id": command_log.id,
            }

        except Exception as e:
            command_log.log_status = "failed"
            command_log.error_message = str(e)
            await self.db.flush()
            return {"success": False, "message": str(e)}

        finally:
            connection_pool.release(device_id, client)

    async def write(
        self,
        device_id: int,
        tag_code: str,
        value: float,
        user_id: int | None = None,
        user_input: str | None = None,
        ai_reasoning: str | None = None,
        skip_confirmation: bool = False,
    ) -> dict[str, Any]:
        """
        写入 PLC 点位值

        Args:
            device_id: 设备 ID
            tag_code: 点位编码
            value: 目标值
            user_id: 用户 ID
            user_input: 用户原始输入
            ai_reasoning: AI 推理过程
            skip_confirmation: 是否跳过确认检查（确认后执行时使用）

        Returns:
            {"success": bool, "value": float, "unit": str, "message": str, "requires_confirmation": bool}
        """
        # 1. 获取点位元数据
        tag_meta = await self._get_tag_meta(device_id, tag_code)
        if not tag_meta:
            return {"success": False, "message": f"未找到点位: {device_id}/{tag_code}"}

        device = tag_meta.device

        # 2. 权限检查
        if tag_meta.access_type == "READ":
            return {"success": False, "message": "该点位只读，禁止写入"}

        # 3. 范围校验
        if not (tag_meta.min_value <= value <= tag_meta.max_value):
            return {
                "success": False,
                "message": f"值 {value} 超出安全范围 [{tag_meta.min_value}, {tag_meta.max_value}]",
            }

        # 4. 检查是否需要人工确认
        if not skip_confirmation:
            confirmation_result = self._check_confirmation_required(tag_meta, value)
            if confirmation_result["required"]:
                return {
                    "success": False,
                    "requires_confirmation": True,
                    "message": f"操作需要人工确认: {confirmation_result['reason']}",
                }

        # 5. 执行写入
        return await self._execute_write(
            device=device,
            tag=tag_meta,
            value=value,
            user_id=user_id,
            user_input=user_input,
            ai_reasoning=ai_reasoning,
        )

    async def _execute_write(
        self,
        device: DeviceModel,
        tag: TagPointModel,
        value: float,
        user_id: int | None,
        user_input: str | None = None,
        ai_reasoning: str | None = None,
    ) -> dict[str, Any]:
        """执行写入操作"""
        # 记录操作日志
        command_log = CommandLogModel(
            user_id=user_id,
            device_id=device.id,
            tag_id=tag.id,
            action="WRITE",
            request_value=value,
            log_status="pending",
            user_input=user_input,
            ai_reasoning=ai_reasoning,
        )
        self.db.add(command_log)
        await self.db.flush()

        start_time = time.time()

        # 获取连接
        client = connection_pool.acquire(device.id)
        if not client:
            command_log.log_status = "failed"
            command_log.error_message = "无法获取设备连接"
            await self.db.flush()
            return {"success": False, "message": "无法获取设备连接"}

        try:
            # 数值转换
            if tag.register_type == "coil":
                raw_value = 1 if value else 0
            else:
                raw_value = self._convert_engineering_to_raw(value, tag)

            # 地址转换
            address = self._normalize_address(tag.address, tag.register_type)

            # 写入寄存器
            if tag.register_type == "coil":
                result = client.write_single_coil(
                    address, bool(raw_value), slave=device.slave_id
                )
            else:
                result = client.write_single_register(
                    address, raw_value, slave=device.slave_id
                )

            if not result.get("success"):
                command_log.log_status = "failed"
                command_log.error_message = result.get("error", "写入失败")
                await self.db.flush()
                return {"success": False, "message": result.get("error", "写入失败")}

            # 更新缓存
            tag.current_value = value
            tag.last_updated = datetime.now()

            # 更新日志
            command_log.log_status = "success"
            command_log.actual_value = value
            command_log.execution_time = (time.time() - start_time) * 1000
            command_log.executed_at = datetime.now()
            await self.db.flush()

            logger.info(
                f"PLC 写入成功: 设备={device.name}, 点位={tag.name}, 值={value} {tag.unit or ''}"
            )

            return {
                "success": True,
                "value": value,
                "unit": tag.unit,
                "message": f"写入成功: {value} {tag.unit or ''}",
                # 结构化数据
                "device_id": device.id,
                "device_name": device.name,
                "tag_id": tag.id,
                "tag_name": tag.name,
                "request_value": value,
                "actual_value": value,
                "execution_time_ms": int((time.time() - start_time) * 1000),
                "command_log_id": command_log.id,
            }

        except Exception as e:
            command_log.log_status = "failed"
            command_log.error_message = str(e)
            await self.db.flush()
            return {"success": False, "message": str(e)}

        finally:
            connection_pool.release(device.id, client)

    async def adjust(
        self,
        device_id: int,
        tag_code: str,
        delta: float,
        user_id: int | None = None,
        user_input: str | None = None,
        ai_reasoning: str | None = None,
    ) -> dict[str, Any]:
        """
        调整参数增量（先读取，再写入）

        例如：温度调高5度 = 读取当前值(85) + 计算(90) + 写入
        """
        # 1. 读取当前值
        read_result = await self.read(device_id, tag_code, user_id)
        if not read_result["success"]:
            return read_result

        current_value = read_result["value"]
        new_value = current_value + delta

        # 2. 写入新值
        write_result = await self.write(
            device_id=device_id,
            tag_code=tag_code,
            value=new_value,
            user_id=user_id,
            user_input=user_input,
            ai_reasoning=ai_reasoning,
        )

        # 3. 增强返回信息
        if write_result.get("success"):
            write_result["previous_value"] = current_value
            write_result["delta"] = delta
            write_result["message"] = (
                f"调整成功: {current_value} → {new_value} {read_result['unit'] or ''} "
                f"(变化: {'+' if delta > 0 else ''}{delta})"
            )

        return write_result

    async def search_devices(self, keyword: str) -> dict[str, Any]:
        """
        搜索设备（用于 AI 设备匹配）

        匹配规则:
        1. 设备名称包含关键词 - 权重 100
        2. 设备编码包含关键词 - 权重 90
        3. 设备描述包含关键词 - 权重 70

        Args:
            keyword: 设备关键词

        Returns:
            {
                "results": [...],
                "disambiguation_needed": bool,
                "disambiguation_hint": str,
                "disambiguation_options": [...]
            }
        """
        keyword = keyword.lower().strip()
        results = []

        stmt = select(DeviceModel).where(DeviceModel.is_active == True)
        devices = (await self.db.execute(stmt)).scalars().all()

        for device in devices:
            score = 0
            match_type = []

            # 设备名称匹配 (权重 100)
            if keyword and keyword in device.name.lower():
                score = 100
                match_type.append("设备名称")

            # 设备编码匹配 (权重 90)
            if device.code and keyword and keyword in device.code.lower():
                score = max(score, 90)
                match_type.append("设备编码")

            # 设备描述匹配 (权重 70)
            if device.description and keyword and keyword in device.description.lower():
                score = max(score, 70)
                match_type.append("设备描述")

            # 空关键词时返回所有设备（用于消歧场景）
            if not keyword:
                score = 50
                match_type.append("全部设备")

            if score > 0:
                results.append(
                    {
                        "device_id": device.id,
                        "device_name": device.name,
                        "device_code": device.code,
                        "slave_id": device.slave_id,
                        "description": device.description,
                        "match_score": score,
                        "match_type": match_type,
                    }
                )

        # 按分数降序排序
        results.sort(key=lambda x: x["match_score"], reverse=True)

        # 判断是否需要消歧
        disambiguation_needed = False
        disambiguation_hint = ""
        disambiguation_options = []

        if len(results) >= 2:
            # 分差 <= 20 触发消歧
            score_diff = results[0]["match_score"] - results[1]["match_score"]
            if score_diff <= 20:
                disambiguation_needed = True
                disambiguation_options = [
                    {
                        "index": i + 1,
                        "device_id": r["device_id"],
                        "device_name": r["device_name"],
                        "description": r.get("description", ""),
                    }
                    for i, r in enumerate(results[:5])
                ]
                options_text = "\n".join(
                    [
                        f"{opt['index']}. {opt['device_name']}"
                        + (f"（{opt['description']}）" if opt["description"] else "")
                        for opt in disambiguation_options
                    ]
                )
                disambiguation_hint = f"检测到多个设备匹配，请选择：\n{options_text}"
        elif len(results) == 0:
            disambiguation_needed = True
            all_devices = (
                await self.db.execute(
                    select(DeviceModel).where(DeviceModel.is_active == True)
                )
            ).scalars().all()
            disambiguation_options = [
                {
                    "index": i + 1,
                    "device_id": d.id,
                    "device_name": d.name,
                    "description": d.description or "",
                }
                for i, d in enumerate(all_devices[:5])
            ]
            options_text = "\n".join(
                [
                    f"{opt['index']}. {opt['device_name']}"
                    + (f"（{opt['description']}）" if opt["description"] else "")
                    for opt in disambiguation_options
                ]
            )
            disambiguation_hint = f"未找到匹配的设备，请选择：\n{options_text}"

        return {
            "results": results,
            "disambiguation_needed": disambiguation_needed,
            "disambiguation_hint": disambiguation_hint,
            "disambiguation_options": disambiguation_options,
        }

    async def search_tags_in_device(
        self, device_id: int, query: str
    ) -> dict[str, Any]:
        """
        在指定设备下搜索点位（用于 AI 点位匹配）

        匹配规则:
        1. 点位名称包含关键词 - 权重 80
        2. 点位别名包含关键词 - 权重 70
        3. 点位编码包含关键词 - 权重 60
        4. 点位描述包含关键词 - 权重 50

        Args:
            device_id: 设备 ID
            query: 点位关键词

        Returns:
            {
                "results": [...],
                "disambiguation_needed": bool,
                "disambiguation_hint": str,
                "disambiguation_options": [...]
            }
        """
        query = query.lower().strip()
        results = []

        stmt = select(TagPointModel).where(
            TagPointModel.device_id == device_id, TagPointModel.is_active == True
        )
        tags = (await self.db.execute(stmt)).scalars().all()

        for tag in tags:
            score = 0
            match_type = []

            # 点位名称匹配 (权重 80)
            if query and query in tag.name.lower():
                score = 80
                match_type.append("点位名称")

            # 点位别名匹配 (权重 70)
            if tag.aliases and query:
                for alias in tag.aliases:
                    if query in alias.lower():
                        score = max(score, 70)
                        match_type.append("点位别名")
                        break

            # 点位编码匹配 (权重 60)
            if query and query in tag.code.lower():
                score = max(score, 60)
                match_type.append("点位编码")

            # 点位描述匹配 (权重 50)
            if tag.description and query and query in tag.description.lower():
                score = max(score, 50)
                match_type.append("点位描述")

            # 空关键词时返回所有点位（用于消歧场景）
            if not query:
                score = 40
                match_type.append("全部点位")

            if score > 0:
                results.append(
                    {
                        "tag_id": tag.id,
                        "tag_name": tag.name,
                        "tag_code": tag.code,
                        "device_id": device_id,
                        "address": tag.address,
                        "register_type": tag.register_type,
                        "data_type": tag.data_type,
                        "access_type": tag.access_type,
                        "min_value": tag.min_value,
                        "max_value": tag.max_value,
                        "unit": tag.unit,
                        "scale_factor": tag.scale_factor,
                        "offset": tag.offset,
                        "requires_confirmation": tag.requires_confirmation,
                        "confirmation_threshold": tag.confirmation_threshold,
                        "current_value": tag.current_value,
                        "description": tag.description,
                        "match_score": score,
                        "match_type": match_type,
                    }
                )

        # 按分数降序排序
        results.sort(key=lambda x: x["match_score"], reverse=True)

        # 判断是否需要消歧
        disambiguation_needed = False
        disambiguation_hint = ""
        disambiguation_options = []

        if len(results) >= 2:
            score_diff = results[0]["match_score"] - results[1]["match_score"]
            if score_diff <= 20:
                disambiguation_needed = True
                disambiguation_options = [
                    {
                        "index": i + 1,
                        "tag_id": r["tag_id"],
                        "tag_name": r["tag_name"],
                        "description": r.get("description", ""),
                        "unit": r.get("unit", ""),
                    }
                    for i, r in enumerate(results[:5])
                ]
                options_text = "\n".join(
                    [
                        f"{opt['index']}. {opt['tag_name']}"
                        + (f"（{opt['description']}）" if opt["description"] else "")
                        for opt in disambiguation_options
                    ]
                )
                disambiguation_hint = f"检测到多个点位匹配，请选择：\n{options_text}"
        elif len(results) == 0:
            disambiguation_needed = True
            all_tags = (
                await self.db.execute(
                    select(TagPointModel).where(
                        TagPointModel.device_id == device_id,
                        TagPointModel.is_active == True,
                    )
                )
            ).scalars().all()
            disambiguation_options = [
                {
                    "index": i + 1,
                    "tag_id": t.id,
                    "tag_name": t.name,
                    "description": t.description or "",
                    "unit": t.unit or "",
                }
                for i, t in enumerate(all_tags[:5])
            ]
            options_text = "\n".join(
                [
                    f"{opt['index']}. {opt['tag_name']}"
                    + (f"（{opt['description']}）" if opt["description"] else "")
                    for opt in disambiguation_options
                ]
            )
            disambiguation_hint = f"未找到匹配的点位，请选择：\n{options_text}"

        return {
            "results": results,
            "disambiguation_needed": disambiguation_needed,
            "disambiguation_hint": disambiguation_hint,
            "disambiguation_options": disambiguation_options,
        }

    async def _get_tag_meta(
        self, device_id: int, tag_code: str
    ) -> TagPointModel | None:
        """
        获取点位元数据

        支持通过以下方式查找点位：
        1. 点位编码（code）- 如 temp_setpoint
        2. 点位名称（name）- 如 温度设定值
        """
        # 先尝试通过编码查找
        stmt = (
            select(TagPointModel)
            .options(selectinload(TagPointModel.device))
            .where(
                TagPointModel.device_id == device_id,
                TagPointModel.code == tag_code,
                TagPointModel.is_active == True,
            )
        )
        tag = (await self.db.execute(stmt)).scalar_one_or_none()

        # 如果通过编码找不到，尝试通过名称查找
        if not tag:
            stmt = (
                select(TagPointModel)
                .options(selectinload(TagPointModel.device))
                .where(
                    TagPointModel.device_id == device_id,
                    TagPointModel.name == tag_code,
                    TagPointModel.is_active == True,
                )
            )
            tag = (await self.db.execute(stmt)).scalar_one_or_none()

        return tag

    def _check_confirmation_required(
        self, tag: TagPointModel, value: float
    ) -> dict[str, Any]:
        """检查是否需要人工确认"""
        # 强制确认点位
        if tag.requires_confirmation:
            return {"required": True, "reason": "该点位配置为需要人工确认"}

        # 阈值确认
        if tag.confirmation_threshold:
            range_size = tag.max_value - tag.min_value
            threshold_value = tag.min_value + range_size * tag.confirmation_threshold

            if abs(value) >= threshold_value:
                return {
                    "required": True,
                    "reason": f"值 {value} 超过安全阈值的 {tag.confirmation_threshold * 100}%",
                }

        return {"required": False, "reason": ""}

    async def create_pending_confirm(
        self,
        device: DeviceModel,
        tag: TagPointModel,
        value: float,
        user_id: int | None,
        user_input: str | None = None,
        ai_reasoning: str | None = None,
    ) -> PendingConfirmModel:
        """创建待确认记录"""
        expire_minutes = ModbusConfigService.DEFAULTS.get("modbus_pending_expire_minutes", 10)
        if self._redis:
            expire_minutes = await ModbusConfigService.get(self._redis, "modbus_pending_expire_minutes")

        expires_at = datetime.now() + timedelta(minutes=expire_minutes)

        pending = PendingConfirmModel(
            user_id=user_id,
            device_name=device.name,
            tag_name=tag.name,
            target_value=value,
            unit=tag.unit,
            confirm_status="pending",
            expires_at=expires_at,
            user_input=user_input,
            ai_explanation=ai_reasoning,
        )
        self.db.add(pending)
        await self.db.flush()

        return pending

    def _convert_raw_to_engineering(
        self, raw_value: int, tag: TagPointModel
    ) -> float:
        """原始值 → 工程值: 工程值 = 原始值 * scale_factor + offset"""
        return raw_value * tag.scale_factor + tag.offset

    def _convert_engineering_to_raw(self, value: float, tag: TagPointModel) -> int:
        """工程值 → 原始值: 原始值 = (工程值 - offset) / scale_factor"""
        return int((value - tag.offset) / tag.scale_factor)

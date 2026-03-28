"""
PLC 操作服务层（同步版本）

用于 Agent 服务，因为 LangChain tool 需要同步函数。
"""

import logging
import time
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.plugin.module_modbus.control.services.connection_pool import connection_pool
from app.plugin.module_modbus.models import (
    CommandLogModel,
    DeviceModel,
    TagPointModel,
)

logger = logging.getLogger(__name__)


class SyncPLCService:
    """PLC 操作服务 - 同步版本，用于 Agent 服务"""

    def __init__(self, db: Session):
        self.db = db

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

    def _get_tag_meta(self, device_id: int, tag_code: str):
        """获取点位元数据（包含设备信息）"""
        stmt = (
            select(TagPointModel)
            .where(TagPointModel.device_id == device_id)
            .where(TagPointModel.code == tag_code)
        )
        tag = self.db.execute(stmt).scalar_one_or_none()
        return tag

    def _convert_raw_to_engineering(self, raw_value: int, tag) -> float:
        """原始值转换为工程值"""
        value = raw_value * tag.scale_factor + tag.offset
        return round(value, 2)

    def _convert_engineering_to_raw(self, value: float, tag) -> int:
        """工程值转换为原始值"""
        raw = (value - tag.offset) / tag.scale_factor
        return int(round(raw))

    def read(self, device_id: int, tag_code: str, user_id: int = None) -> dict[str, Any]:
        """读取 PLC 点位值"""
        # 1. 获取点位元数据
        tag_meta = self._get_tag_meta(device_id, tag_code)
        if not tag_meta:
            return {"success": False, "message": f"未找到点位: {device_id}/{tag_code}"}

        stmt = select(DeviceModel).where(DeviceModel.id == device_id)
        device = self.db.execute(stmt).scalar_one_or_none()
        if not device:
            return {"success": False, "message": f"未找到设备: {device_id}"}

        # 2. 记录操作日志
        command_log = CommandLogModel(
            user_id=user_id,
            device_id=device_id,
            tag_id=tag_meta.id,
            action="READ",
            status="pending",
        )
        self.db.add(command_log)
        self.db.flush()

        start_time = time.time()

        # 3. 获取连接
        client = connection_pool.acquire(device_id)
        if not client:
            command_log.status = "failed"
            command_log.error_message = "无法获取设备连接"
            self.db.commit()
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
                return {"success": False, "message": f"不支持的寄存器类型: {tag_meta.register_type}"}

            if not result.get("success"):
                command_log.status = "failed"
                command_log.error_message = result.get("error", "读取失败")
                self.db.commit()
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
            command_log.status = "success"
            command_log.actual_value = value
            command_log.execution_time = (time.time() - start_time) * 1000
            command_log.executed_at = datetime.now()
            self.db.commit()

            return {
                "success": True,
                "value": value,
                "raw_value": raw_value,
                "unit": tag_meta.unit,
                "message": f"当前值: {value} {tag_meta.unit or ''}",
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
            command_log.status = "failed"
            command_log.error_message = str(e)
            self.db.commit()
            return {"success": False, "message": str(e)}

        finally:
            connection_pool.release(device_id, client)

    def write(
        self,
        device_id: int,
        tag_code: str,
        value: float,
        user_id: int = None,
        user_input: str = None,
        ai_reasoning: str = None,
        skip_confirmation: bool = False,
    ) -> dict[str, Any]:
        """写入 PLC 点位值"""
        # 1. 获取点位元数据
        tag_meta = self._get_tag_meta(device_id, tag_code)
        if not tag_meta:
            return {"success": False, "message": f"未找到点位: {device_id}/{tag_code}"}

        stmt = select(DeviceModel).where(DeviceModel.id == device_id)
        device = self.db.execute(stmt).scalar_one_or_none()
        if not device:
            return {"success": False, "message": f"未找到设备: {device_id}"}

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
        return self._execute_write(
            device=device,
            tag=tag_meta,
            value=value,
            user_id=user_id,
            user_input=user_input,
            ai_reasoning=ai_reasoning,
        )

    def _check_confirmation_required(self, tag, value: float) -> dict[str, Any]:
        """检查是否需要人工确认"""
        reasons = []

        # 1. 点位配置了强制确认
        if tag.requires_confirmation:
            reasons.append("该点位配置了人工确认")

        # 2. 阈值确认
        if tag.confirmation_threshold:
            if abs(value) > tag.confirmation_threshold:
                reasons.append(f"值 {value} 超过确认阈值 {tag.confirmation_threshold}")

        # 3. 安全关键点（名称或编码中包含关键标识）
        critical_keywords = ["紧急", "安全", "停止", "急停", "emergency", "stop", "safety"]
        tag_identifier = f"{tag.name} {tag.code}".lower()
        if any(kw in tag_identifier for kw in critical_keywords):
            reasons.append("该点位涉及安全关键操作")

        return {
            "required": len(reasons) > 0,
            "reason": "; ".join(reasons) if reasons else None,
        }

    def _execute_write(
        self,
        device: DeviceModel,
        tag: TagPointModel,
        value: float,
        user_id: int = None,
        user_input: str = None,
        ai_reasoning: str = None,
    ) -> dict[str, Any]:
        """执行写入操作"""
        # 记录操作日志
        command_log = CommandLogModel(
            user_id=user_id,
            device_id=device.id,
            tag_id=tag.id,
            action="WRITE",
            request_value=value,
            status="pending",
            user_input=user_input,
            ai_reasoning=ai_reasoning,
            confirmation_required=False,
        )
        self.db.add(command_log)
        self.db.flush()

        start_time = time.time()

        # 获取连接
        client = connection_pool.acquire(device.id)
        if not client:
            command_log.status = "failed"
            command_log.error_message = "无法获取设备连接"
            self.db.commit()
            return {"success": False, "message": "无法获取设备连接"}

        try:
            # 转换值
            raw_value = self._convert_engineering_to_raw(value, tag)
            address = self._normalize_address(tag.address, tag.register_type)

            if tag.register_type == "holding":
                result = client.write_single_register(address, raw_value, slave=device.slave_id)
            elif tag.register_type == "coil":
                result = client.write_single_coil(address, bool(value), slave=device.slave_id)
            else:
                return {"success": False, "message": f"不支持的写入类型: {tag.register_type}"}

            if not result.get("success"):
                command_log.status = "failed"
                command_log.error_message = result.get("error", "写入失败")
                self.db.commit()
                return {"success": False, "message": result.get("error", "写入失败")}

            # 更新缓存
            tag.current_value = value
            tag.last_updated = datetime.now()

            # 更新日志
            command_log.status = "success"
            command_log.actual_value = value
            command_log.execution_time = (time.time() - start_time) * 1000
            command_log.executed_at = datetime.now()
            self.db.commit()

            return {
                "success": True,
                "value": value,
                "unit": tag.unit,
                "message": f"已写入: {value} {tag.unit or ''}",
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
            command_log.status = "failed"
            command_log.error_message = str(e)
            self.db.commit()
            return {"success": False, "message": str(e)}

        finally:
            connection_pool.release(device.id, client)

    def adjust(
        self,
        device_id: int,
        tag_code: str,
        delta: float,
        user_id: int = None,
        user_input: str = None,
    ) -> dict[str, Any]:
        """调整 PLC 点位值（增量）"""
        # 1. 获取点位元数据
        tag_meta = self._get_tag_meta(device_id, tag_code)
        if not tag_meta:
            return {"success": False, "message": f"未找到点位: {device_id}/{tag_code}"}

        # 2. 先读取当前值
        read_result = self.read(device_id, tag_code, user_id)
        if not read_result["success"]:
            return read_result

        current_value = read_result["value"]
        target_value = current_value + delta

        # 3. 执行写入
        write_result = self.write(
            device_id=device_id,
            tag_code=tag_code,
            value=target_value,
            user_id=user_id,
            user_input=user_input,
            ai_reasoning=f"增量调整: {current_value} + {delta} = {target_value}",
        )

        if write_result["success"]:
            write_result["previous_value"] = current_value
            write_result["delta"] = delta
            write_result["message"] = f"已调整: {current_value} → {target_value} ({'+' if delta > 0 else ''}{delta})"

        return write_result

    def search_devices(self, keyword: str = None) -> dict[str, Any]:
        """搜索设备"""
        stmt = select(DeviceModel)
        if keyword:
            stmt = stmt.where(
                DeviceModel.name.ilike(f"%{keyword}%")
                | DeviceModel.code.ilike(f"%{keyword}%")
            )

        devices = self.db.execute(stmt).scalars().all()

        if not devices:
            return {
                "results": [],
                "disambiguation_needed": False,
                "disambiguation_hint": "未找到匹配的设备，请尝试其他关键词。",
            }

        results = []
        for device in devices:
            score = 100 if keyword and keyword.lower() in device.name.lower() else 50

            results.append({
                "device_id": device.id,
                "device_name": device.name,
                "device_code": device.code,
                "status": device.device_status,
                "match_score": score,
            })

        # 按匹配分数排序
        results.sort(key=lambda x: x["match_score"], reverse=True)

        # 是否需要消歧
        disambiguation_needed = len(results) > 1
        disambiguation_hint = None

        if disambiguation_needed:
            hint_lines = ["检测到多个设备匹配，请选择："]
            for i, r in enumerate(results, 1):
                hint_lines.append(f"{i}. {r['device_name']} ({r['device_code']})")
            disambiguation_hint = "\n".join(hint_lines)

        return {
            "results": results,
            "disambiguation_needed": disambiguation_needed,
            "disambiguation_hint": disambiguation_hint,
        }

    def search_tags_in_device(self, device_id: int, query: str = None) -> dict[str, Any]:
        """在设备内搜索点位"""
        stmt = select(TagPointModel).where(TagPointModel.device_id == device_id)

        if query:
            # 搜索名称、编码或别名
            stmt = stmt.where(
                TagPointModel.name.ilike(f"%{query}%")
                | TagPointModel.code.ilike(f"%{query}%")
            )

        tags = self.db.execute(stmt).scalars().all()

        if not tags:
            # 如果没有匹配，返回该设备所有点位
            stmt = select(TagPointModel).where(TagPointModel.device_id == device_id)
            all_tags = self.db.execute(stmt).scalars().all()

            if all_tags:
                results = []
                for tag in all_tags:
                    results.append({
                        "tag_id": tag.id,
                        "tag_name": tag.name,
                        "tag_code": tag.code,
                        "unit": tag.unit,
                        "access_type": tag.access_type,
                    })

                hint_lines = [f"未找到匹配 '{query}' 的点位，该设备所有点位如下："]
                for i, t in enumerate(results, 1):
                    hint_lines.append(f"{i}. {t['tag_name']} ({t['tag_code']})")

                return {
                    "results": [],
                    "disambiguation_needed": True,
                    "disambiguation_hint": "\n".join(hint_lines),
                    "disambiguation_options": results,
                }

            return {
                "results": [],
                "disambiguation_needed": False,
                "disambiguation_hint": "该设备没有配置点位。",
            }

        results = []
        for tag in tags:
            score = 100 if query and query.lower() in tag.name.lower() else 50

            results.append({
                "tag_id": tag.id,
                "tag_name": tag.name,
                "tag_code": tag.code,
                "unit": tag.unit,
                "access_type": tag.access_type,
                "match_score": score,
            })

        results.sort(key=lambda x: x["match_score"], reverse=True)

        disambiguation_needed = len(results) > 1
        disambiguation_hint = None

        if disambiguation_needed:
            hint_lines = ["检测到多个点位匹配，请选择："]
            for i, r in enumerate(results, 1):
                hint_lines.append(f"{i}. {r['tag_name']} ({r['unit'] or ''})")
            disambiguation_hint = "\n".join(hint_lines)

        return {
            "results": results,
            "disambiguation_needed": disambiguation_needed,
            "disambiguation_hint": disambiguation_hint,
            "disambiguation_options": results if disambiguation_needed else [],
        }

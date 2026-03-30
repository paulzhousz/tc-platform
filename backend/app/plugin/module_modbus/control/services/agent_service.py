"""
LLM Agent 服务

基于 LangChain 1.x 实现 PLC 控制的智能对话代理。
支持设备搜索、点位操作、消歧确认等功能。
"""

import json
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.config.setting import settings
from app.plugin.module_modbus.control.services.config_service import ModbusConfigService
from app.plugin.module_modbus.control.services.plc_service import PLCService
from app.plugin.module_modbus.models import AgentSessionModel, DeviceModel

logger = logging.getLogger(__name__)


def load_system_prompt() -> str:
    """从配置文件加载系统提示词"""
    # agent_service.py -> services -> control -> module_modbus/config/
    prompt_path = Path(__file__).parent.parent.parent / "config" / "modbus_system_prompt.md"
    try:
        with open(prompt_path, encoding="utf-8") as f:
            content = f.read()
        logger.info(f"系统提示词加载成功: {prompt_path}")
        return content
    except Exception as e:
        logger.error(f"加载系统提示词文件失败: {e}")
        return """你是一个资深的工业自动化专家和 PLC 控制智能体。请使用工具完成用户的操作请求。"""


# 系统提示词（从文件加载）
SYSTEM_PROMPT = load_system_prompt()


def _extract_operation_intent(chat_history: list[dict]) -> dict[str, Any] | None:
    """
    从对话历史中提取用户的原始操作意图

    Returns:
        {
            "operation": "read" | "write" | "adjust",
            "tag": "温度" | "设定温度" 等,
            "value": 30 等 (对于 write/adjust),
            "delta": 5 或 -5 (对于 adjust),
            "raw_message": "空调温度调为30度"
        }
    """
    import re

    if not chat_history:
        return None

    # 找到最近一条用户原始消息（不是消歧回复）
    for msg in reversed(chat_history):
        content = msg.get("content", "").strip()
        role = msg.get("role", "")

        if role != "user":
            continue

        # 跳过消歧回复
        if content.isdigit() and len(content) <= 2:
            continue
        if content in ["确认", "取消", "是", "否", "好的", "执行"]:
            continue

        # 找到了原始消息，解析操作意图
        intent = {
            "raw_message": content,
            "operation": None,
            "tag": None,
            "value": None,
            "delta": None,
        }

        # 解析操作类型
        if any(kw in content for kw in ["查看", "读取", "显示", "是多少", "什么"]):
            intent["operation"] = "read"
        elif any(kw in content for kw in ["设定", "设置", "改为", "设为", "调为"]):
            intent["operation"] = "write"
        elif any(kw in content for kw in ["调高", "增加", "提高", "调大"]):
            intent["operation"] = "adjust"
            intent["delta"] = 5
        elif any(kw in content for kw in ["调低", "降低", "减少", "调小"]):
            intent["operation"] = "adjust"
            intent["delta"] = -5

        # 提取数值
        value_patterns = [
            r"(\d+)\s*度",
            r"设[为定]\s*(\d+)",
            r"改[为为]\s*(\d+)",
            r"调[为高降低大]\s*(\d+)",
            r"[高低]\s*(\d+)",
            r"(\d+)度",
        ]
        for pattern in value_patterns:
            match = re.search(pattern, content)
            if match:
                intent["value"] = int(match.group(1))
                break

        # 提取点位关键词
        tag_patterns = ["温度", "设定温度", "湿度", "风速", "模式", "开关"]
        for tag in tag_patterns:
            if tag in content:
                intent["tag"] = tag
                break

        logger.info(f"[Agent] 提取操作意图: {intent}")
        return intent

    return None


def _preprocess_user_message(
    session: AgentSessionModel, message: str
) -> tuple[str, str | None, bool, bool, bool]:
    """
    预处理用户消息，检查消歧/确认上下文并注入提示

    Returns:
        (processed_message, context_hint, should_clear_disambiguation, should_clear_pending, skip_user_message)
        skip_user_message: 为 True 时表示消歧处理已完成，不需要再添加原始用户消息
    """
    context = session.operation_context or {}
    context_hint = None
    should_clear_disambiguation = False
    should_clear_pending = False
    skip_user_message = False

    logger.info(
        f"[Agent] 预处理用户消息: '{message}', operation_context keys: {list(context.keys())}"
    )

    # 检查是否有待确认操作
    pending = context.get("pending_confirmation")
    if pending:
        logger.info(f"[Agent] 检测到待确认操作: {pending.get('tag_name')}")
        if message.strip() in ["1", "确认", "是", "好的", "执行", "确认执行"]:
            context_hint = f"""[系统提示] 用户回复 "{message}"，这是对操作确认的肯定回复。
请立即调用 confirm_operation() 执行待确认的操作。
待确认操作：设备={pending['device_name']}，点位={pending['tag_name']}，值={pending['value']}"""
        elif message.strip() in ["2", "取消", "不要", "否", "取消操作"]:
            context_hint = f"""[系统提示] 用户回复 "{message}"，这是对操作确认的否定回复。
请立即调用 cancel_operation() 取消待确认的操作。"""
        else:
            logger.info("[Agent] 用户发送了新消息，自动取消待确认操作")
            should_clear_pending = True
            context_hint = """[系统提示] 用户发送了新请求，之前的待确认操作已自动取消。请处理用户的新请求。"""
        return message, context_hint, should_clear_disambiguation, should_clear_pending, False

    # 检查是否有消歧上下文
    disambiguation = context.get("disambiguation_context")
    if disambiguation:
        disambig_type = disambiguation.get("type")
        options = disambiguation.get("options", [])
        logger.info(
            f"[Agent] 检测到消歧上下文: type={disambig_type}, options_count={len(options)}"
        )

        selected = None

        # 数字选择
        try:
            idx = int(message.strip()) - 1
            if 0 <= idx < len(options):
                selected = options[idx]
                logger.info(f"[Agent] 数字选择: idx={idx}, selected={selected.get('name')}")
        except (ValueError, IndexError):
            pass

        # 文字匹配
        if not selected:
            msg_lower = message.strip().lower()
            for opt in options:
                if opt["name"].lower() == msg_lower:
                    selected = opt
                    logger.info(f"[Agent] 文字匹配: selected={opt.get('name')}")
                    break
                for kw in opt.get("keywords", []):
                    if kw.lower() in msg_lower or msg_lower in kw.lower():
                        selected = opt
                        logger.info(f"[Agent] 关键词匹配: selected={opt.get('name')}")
                        break

        if selected:
            should_clear_disambiguation = True
            if disambig_type == "device":
                # 设备消歧后，提取原始意图并告知 LLM 搜索什么点位
                intent = _extract_operation_intent(session.chat_history or [])
                skip_user_message = True  # 消歧完成，跳过原始用户消息

                if intent:
                    tag_keyword = intent.get("tag", "")
                    operation = intent.get("operation", "read")
                    context_hint = f"""[系统提示] 用户选择了设备 "{selected['name']}"（device_id={selected['id']}）。
原始请求是"{intent['raw_message']}"。
请立即调用 search_tag_mapping(device_id={selected['id']}, query="{tag_keyword}") 搜索点位。
如果找到唯一点位，直接执行{operation}操作。"""
                else:
                    context_hint = f"""[系统提示] 用户选择了设备 "{selected['name']}"（device_id={selected['id']}）。
请使用 device_id={selected['id']} 调用 search_tag_mapping 搜索相关点位。"""
            elif disambig_type == "tag":
                skip_user_message = True  # 消歧完成，跳过原始用户消息
                intent = _extract_operation_intent(session.chat_history or [])

                if intent:
                    device_id = selected.get("device_id")
                    tag_name = selected["name"]
                    operation = intent.get("operation", "write")

                    if operation == "write" and intent.get("value"):
                        context_hint = f"""[系统提示] 用户选择了点位 "{tag_name}"。
原始请求是"{intent['raw_message']}"，请立即调用 write_plc(device_id={device_id}, tag_name="{tag_name}", value={intent['value']}) 执行写入操作。
不要再搜索点位，直接执行写入！"""
                    elif operation == "adjust" and intent.get("delta"):
                        context_hint = f"""[系统提示] 用户选择了点位 "{tag_name}"。
原始请求是"{intent['raw_message']}"，请立即调用 adjust_plc(device_id={device_id}, tag_name="{tag_name}", delta={intent['delta']}) 执行调整操作。
不要再搜索点位，直接执行调整！"""
                    elif operation == "read":
                        context_hint = f"""[系统提示] 用户选择了点位 "{tag_name}"。
原始请求是"{intent['raw_message']}"，请立即调用 read_plc(device_id={device_id}, tag_name="{tag_name}") 执行读取操作。
不要再搜索点位，直接执行读取！"""
                    else:
                        context_hint = f"""[系统提示] 用户选择了点位 "{tag_name}"（device_id={device_id}）。
请根据原始请求 "{intent['raw_message']}" 执行相应的 PLC 操作。"""
                else:
                    context_hint = f"""[系统提示] 用户选择了点位 "{selected['name']}"（device_id={selected.get('device_id')}）。
请根据对话上下文执行相应的 PLC 操作。"""
        else:
            logger.info("[Agent] 用户输入不匹配任何消歧选项，清除消歧上下文")
            should_clear_disambiguation = True
            context_hint = """[系统提示] 用户发送了新请求，之前的消歧已取消。请处理用户的新请求。"""
    else:
        logger.info("[Agent] 无消歧上下文")

    return message, context_hint, should_clear_disambiguation, should_clear_pending, skip_user_message


class AgentService:
    """LLM Agent 服务"""

    def __init__(self, db: AsyncSession, config: dict[str, Any] | None = None):
        self.db = db
        self._config = config or ModbusConfigService.DEFAULTS.copy()
        self._agent = None
        self._tools = None
        self._current_session: AgentSessionModel | None = None

    def get_tools(self, user_id: int) -> list:
        """获取工具列表（绑定当前用户）"""
        if self._tools is None:
            plc_service = PLCService(self.db)

            @tool
            async def search_device(keyword: str) -> str:
                """
                搜索设备。
                当用户提到设备名称时使用此工具搜索设备。
                输入：设备关键词（如"空调"、"智能空调"），可为空返回所有设备
                返回：匹配的设备列表，包含 device_id、match_score、disambiguation_info
                """
                logger.info(f"[Agent Tool] search_device 被调用, keyword={keyword}")
                result = await plc_service.search_devices(keyword)
                if not result["results"]:
                    logger.info("[Agent Tool] search_device 未找到结果")
                    return f"未找到匹配的设备。{result.get('disambiguation_hint', '')}"

                logger.info(
                    f"[Agent Tool] search_device 找到 {len(result['results'])} 个结果, disambiguation_needed={result['disambiguation_needed']}"
                )

                if result["disambiguation_needed"] and self._current_session:
                    options = [
                        {
                            "id": r["device_id"],
                            "name": r["device_name"],
                            "keywords": [r["device_name"]],
                        }
                        for r in result["results"]
                    ]
                    await self.update_disambiguation_context(
                        self._current_session, "device", options
                    )
                    return f"""DISAMBIGUATION_REQUIRED

检测到多个设备匹配，必须等待用户选择。

{result['disambiguation_hint']}

【重要】你必须停止执行，将以上选项展示给用户，等待用户回复编号或设备名称。不要自己猜测或选择设备！"""

                return json.dumps(result, ensure_ascii=False, indent=2)

            @tool
            async def search_tag_mapping(device_id: int, query: str) -> str:
                """
                在指定设备下搜索点位。
                必须在确定 device_id 后调用此工具。
                参数：
                - device_id: 设备ID（必填，整数）
                - query: 点位关键词（如"温度"、"设定温度"）
                返回：匹配的点位列表，包含 tag_id、tag_name、disambiguation_info
                """
                logger.info(
                    f"[Agent Tool] search_tag_mapping 被调用, device_id={device_id}, query={query}"
                )
                result = await plc_service.search_tags_in_device(device_id, query)

                logger.info(
                    f"[Agent Tool] search_tag_mapping 找到 {len(result['results'])} 个结果, disambiguation_needed={result['disambiguation_needed']}"
                )

                if result["disambiguation_needed"] and self._current_session:
                    options = [
                        {
                            "id": opt["tag_id"],
                            "name": opt["tag_name"],
                            "device_id": device_id,
                            "keywords": [opt["tag_name"]],
                        }
                        for opt in result.get("disambiguation_options", [])
                    ]
                    if options:
                        await self.update_disambiguation_context(
                            self._current_session, "tag", options
                        )
                        return f"""DISAMBIGUATION_REQUIRED

{result['disambiguation_hint']}

【重要】你必须停止执行，将以上选项展示给用户，等待用户回复编号或点位名称。不要自己猜测！"""

                if not result["results"]:
                    return f"在该设备中未找到匹配的功能点。{result.get('disambiguation_hint', '')}"

                return json.dumps(result, ensure_ascii=False, indent=2)

            @tool
            async def read_plc(device_id: int, tag_name: str) -> str:
                """
                从 PLC 读取设备状态或传感器数值。
                参数：
                - device_id: 设备ID（整数）
                - tag_name: 点位编码
                返回：当前数值及单位
                """
                logger.info(
                    f"[Agent Tool] read_plc 被调用, device_id={device_id}, tag_name={tag_name}"
                )
                result = await plc_service.read(device_id, tag_name, user_id)
                if result["success"]:
                    logger.info(f"[Agent Tool] read_plc 成功, value={result['value']}")
                    return json.dumps(
                        {
                            "message": f"读取成功: {result['value']} {result.get('unit', '')}",
                            "status": "success",
                            "data": {
                                "device_id": result.get("device_id"),
                                "device_name": result.get("device_name"),
                                "tag_id": result.get("tag_id"),
                                "tag_name": result.get("tag_name"),
                                "value": result.get("value"),
                                "raw_value": result.get("raw_value"),
                                "unit": result.get("unit"),
                                "min_value": result.get("min_value"),
                                "max_value": result.get("max_value"),
                            },
                            "duration_ms": result.get("execution_time_ms"),
                            "command_log_id": result.get("command_log_id"),
                        },
                        ensure_ascii=False,
                    )
                logger.warning(f"[Agent Tool] read_plc 失败, message={result['message']}")
                return json.dumps(
                    {
                        "message": f"读取失败: {result['message']}",
                        "status": "failed",
                    },
                    ensure_ascii=False,
                )

            @tool
            async def write_plc(device_id: int, tag_name: str, value: float) -> str:
                """
                向 PLC 写入设定值或控制指令。
                参数：
                - device_id: 设备ID（整数）
                - tag_name: 点位编码
                - value: 目标值
                注意：必须先确认设备权限和数值范围
                """
                logger.info(
                    f"[Agent Tool] write_plc 被调用, device_id={device_id}, tag_name={tag_name}, value={value}"
                )
                result = await plc_service.write(device_id, tag_name, value, user_id)
                if result["success"]:
                    logger.info(f"[Agent Tool] write_plc 成功, value={result['value']}")
                    return json.dumps(
                        {
                            "message": f"写入成功: {result['value']} {result.get('unit', '')}",
                            "status": "success",
                            "data": {
                                "device_id": result.get("device_id"),
                                "device_name": result.get("device_name"),
                                "tag_id": result.get("tag_id"),
                                "tag_name": result.get("tag_name"),
                                "value": result.get("value"),
                                "request_value": result.get("request_value"),
                                "actual_value": result.get("actual_value"),
                                "unit": result.get("unit"),
                            },
                            "duration_ms": result.get("execution_time_ms"),
                            "command_log_id": result.get("command_log_id"),
                        },
                        ensure_ascii=False,
                    )
                elif result.get("requires_confirmation"):
                    logger.info("[Agent Tool] write_plc 需要人工确认")

                    # 先获取设备名称
                    stmt = select(DeviceModel).where(DeviceModel.id == device_id)
                    device = (await self.db.execute(stmt)).scalar_one_or_none()
                    device_name = device.name if device else f"设备{device_id}"

                    if self._current_session:
                        await self.update_pending_confirmation(
                            self._current_session,
                            device_id=device_id,
                            device_name=device_name,
                            tag_name=tag_name,
                            value=value,
                            operation="write",
                        )

                    return f"""CONFIRMATION_REQUIRED

操作需要用户确认，已记录待确认状态。

即将执行操作：
- 设备：{device_name}
- 点位：{tag_name}
- 目标值：{value}

请将以下选项展示给用户，等待用户回复：
1. 确认执行
2. 取消

【重要】你只需要展示选项，不要自己调用 confirm_operation 或 cancel_operation。等待用户回复后，下一轮对话再根据用户选择调用相应工具。"""
                logger.warning(f"[Agent Tool] write_plc 失败, message={result['message']}")
                return json.dumps(
                    {
                        "message": f"写入失败: {result['message']}",
                        "status": "failed",
                    },
                    ensure_ascii=False,
                )

            @tool
            async def adjust_plc(device_id: int, tag_name: str, delta: float) -> str:
                """
                调整设备参数的增量值。
                参数：
                - device_id: 设备ID（整数）
                - tag_name: 点位编码
                - delta: 增量值（正数增加，负数减少）
                例如：delta=5 表示增加5个单位
                """
                logger.info(
                    f"[Agent Tool] adjust_plc 被调用, device_id={device_id}, tag_name={tag_name}, delta={delta}"
                )
                result = await plc_service.adjust(device_id, tag_name, delta, user_id)
                if result["success"]:
                    logger.info("[Agent Tool] adjust_plc 成功")
                    return json.dumps(
                        {
                            "message": result.get("message", "调整成功"),
                            "status": "success",
                            "data": {
                                "device_id": result.get("device_id"),
                                "device_name": result.get("device_name"),
                                "tag_id": result.get("tag_id"),
                                "tag_name": result.get("tag_name"),
                                "value": result.get("value"),
                                "previous_value": result.get("previous_value"),
                                "delta": result.get("delta"),
                                "unit": result.get("unit"),
                            },
                            "duration_ms": result.get("execution_time_ms"),
                            "command_log_id": result.get("command_log_id"),
                        },
                        ensure_ascii=False,
                    )
                elif result.get("requires_confirmation"):
                    logger.info("[Agent Tool] adjust_plc 需要人工确认")

                    previous_value = result.get("previous_value", 0)
                    target_value = previous_value + delta

                    # 先获取设备名称
                    stmt = select(DeviceModel).where(DeviceModel.id == device_id)
                    device = (await self.db.execute(stmt)).scalar_one_or_none()
                    device_name = device.name if device else f"设备{device_id}"

                    if self._current_session:
                        await self.update_pending_confirmation(
                            self._current_session,
                            device_id=device_id,
                            device_name=device_name,
                            tag_name=tag_name,
                            value=target_value,
                            operation="adjust",
                        )

                    return f"""CONFIRMATION_REQUIRED

操作需要用户确认，已记录待确认状态。

即将执行操作：
- 设备：{device_name}
- 点位：{tag_name}
- 当前值：{previous_value}
- 调整量：{'+' if delta > 0 else ''}{delta}
- 目标值：{target_value}

请将以下选项展示给用户，等待用户回复：
1. 确认执行
2. 取消

【重要】你只需要展示选项，不要自己调用 confirm_operation 或 cancel_operation。等待用户回复后，下一轮对话再根据用户选择调用相应工具。"""
                logger.warning(f"[Agent Tool] adjust_plc 失败, message={result['message']}")
                return json.dumps(
                    {
                        "message": f"调整失败: {result['message']}",
                        "status": "failed",
                    },
                    ensure_ascii=False,
                )

            @tool
            async def confirm_operation() -> str:
                """
                确认执行待确认的操作。
                当用户回复"确认"、"是"、"执行"时调用此工具。
                无需参数，系统会自动执行之前记录的待确认操作。
                返回：操作执行结果
                """
                logger.info("[Agent Tool] confirm_operation 被调用")

                if not self._current_session:
                    return "错误：无法获取会话信息"

                context = self._current_session.operation_context or {}
                pending = context.get("pending_confirmation")

                if not pending:
                    return "没有待确认的操作。请先发起一个需要确认的操作。"

                result = await plc_service.write(
                    pending["device_id"],
                    pending["tag_name"],
                    pending["value"],
                    user_id,
                    skip_confirmation=True,
                )

                await self.clear_pending_confirmation(self._current_session)

                if result["success"]:
                    logger.info("[Agent Tool] confirm_operation 成功")
                    return f"【操作已完成】{pending['tag_name']} 已成功设为 {pending['value']}。任务完成，无需再调用任何工具。"
                logger.warning(f"[Agent Tool] confirm_operation 失败, message={result['message']}")
                return f"操作执行失败: {result['message']}。任务结束。"

            @tool
            async def cancel_operation() -> str:
                """
                取消待确认的操作。
                当用户回复"取消"、"不要"时调用此工具。
                无需参数。
                返回：取消确认
                """
                logger.info("[Agent Tool] cancel_operation 被调用")

                if not self._current_session:
                    return "错误：无法获取会话信息"

                context = self._current_session.operation_context or {}
                pending = context.get("pending_confirmation")

                if not pending:
                    return "没有待取消的操作。"

                await self.clear_pending_confirmation(self._current_session)
                logger.info("[Agent Tool] cancel_operation 成功")
                return f"操作已取消: {pending['tag_name']} 的写入操作已取消"

            self._tools = [
                search_device,
                search_tag_mapping,
                read_plc,
                write_plc,
                adjust_plc,
                confirm_operation,
                cancel_operation,
            ]

        return self._tools

    def create_agent_graph(self, user_id: int):
        """创建 Agent (LangChain 1.x 版本)"""
        tools = self.get_tools(user_id)

        # 使用 ChatOpenAI 实例
        llm = ChatOpenAI(
            base_url=settings.MODBUS_LLM_BASE_URL,
            api_key=settings.MODBUS_LLM_API_KEY,
            model=self._config.get("modbus_llm_model_name"),
            temperature=self._config.get("modbus_llm_temperature"),
        )

        # 使用 LangChain 1.x 的 create_agent API
        agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
        )
        return agent

    async def _get_or_create_session(self, user_id: int, session_id: str | None = None) -> AgentSessionModel:
        """获取或创建会话"""
        if session_id:
            stmt = select(AgentSessionModel).where(
                AgentSessionModel.session_id == session_id,
                AgentSessionModel.user_id == user_id,
            )
            session = (await self.db.execute(stmt)).scalar_one_or_none()

            if session and not self._is_session_expired(session):
                await self.db.refresh(session)
                session.last_active = datetime.now()
                await self.db.commit()
                logger.info(
                    f"[Agent] 获取会话 {session.session_id}, operation_context type: {type(session.operation_context)}"
                )
                return session

        # 创建新会话
        new_session = AgentSessionModel(
            user_id=user_id,
            session_id=str(uuid.uuid4()),
            ttl_minutes=self._config.get("modbus_llm_session_ttl_minutes"),
        )
        self.db.add(new_session)
        await self.db.commit()
        return new_session

    def _is_session_expired(self, session: AgentSessionModel) -> bool:
        """检查会话是否过期"""
        expires_at = session.last_active + timedelta(minutes=session.ttl_minutes)
        return datetime.now() > expires_at

    def _build_chat_history(self, session: AgentSessionModel) -> list:
        """构建对话历史"""
        history = []
        chat_data = session.chat_history or []

        max_turns = self._config.get("modbus_llm_max_history_turns")
        recent_history = (
            chat_data[-max_turns * 2 :] if len(chat_data) > max_turns * 2 else chat_data
        )

        for msg in recent_history:
            if msg.get("role") == "user":
                history.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                history.append(AIMessage(content=msg.get("content", "")))

        return history

    async def _update_session(self, session: AgentSessionModel, user_message: str, assistant_reply: str):
        """更新会话"""
        from sqlalchemy.orm.attributes import flag_modified

        chat_history = session.chat_history or []

        chat_history.append({"role": "user", "content": user_message})
        chat_history.append({"role": "assistant", "content": assistant_reply})

        max_messages = self._config.get("modbus_llm_max_history_turns", 20) * 2
        if len(chat_history) > max_messages:
            chat_history = chat_history[-max_messages:]

        session.chat_history = chat_history
        flag_modified(session, "chat_history")
        session.last_active = datetime.now()
        await self.db.commit()

    async def update_disambiguation_context(
        self,
        session: AgentSessionModel,
        disambiguation_type: str,
        options: list[dict[str, Any]],
    ):
        """更新消歧上下文"""
        context = session.operation_context or {}

        context["disambiguation_context"] = {
            "type": disambiguation_type,
            "options": options,
            "created_at": datetime.now().isoformat(),
        }

        session.operation_context = context
        flag_modified(session, "operation_context")
        await self.db.commit()
        await self.db.refresh(session)
        logger.info(
            f"[Agent] 更新消歧上下文: type={disambiguation_type}, options_count={len(options)}"
        )

    async def clear_disambiguation_context(self, session: AgentSessionModel):
        """清除消歧上下文"""
        context = session.operation_context or {}
        if "disambiguation_context" in context:
            del context["disambiguation_context"]
            session.operation_context = context
            flag_modified(session, "operation_context")
            await self.db.commit()
            await self.db.refresh(session)
            logger.info("[Agent] 清除消歧上下文")

    async def update_pending_confirmation(
        self,
        session: AgentSessionModel,
        device_id: int,
        device_name: str,
        tag_name: str,
        value: float,
        operation: str = "write",
    ):
        """更新待确认操作上下文"""
        context = session.operation_context or {}

        if "disambiguation_context" in context:
            del context["disambiguation_context"]

        context["pending_confirmation"] = {
            "device_id": device_id,
            "device_name": device_name,
            "tag_name": tag_name,
            "value": value,
            "operation": operation,
            "created_at": datetime.now().isoformat(),
        }

        session.operation_context = context
        flag_modified(session, "operation_context")
        await self.db.commit()
        await self.db.refresh(session)
        logger.info(
            f"[Agent] 更新待确认上下文: device={device_name}, tag={tag_name}, value={value}"
        )

    async def clear_pending_confirmation(self, session: AgentSessionModel):
        """清除待确认上下文"""
        context = session.operation_context or {}
        if "pending_confirmation" in context:
            del context["pending_confirmation"]
            session.operation_context = context
            flag_modified(session, "operation_context")
            await self.db.commit()
            await self.db.refresh(session)
        logger.info("[Agent] 清除待确认上下文")

    async def chat(
        self, user_id: int, message: str, session_id: str | None = None
    ) -> dict[str, Any]:
        """处理对话（同步模式）- LangChain 1.x 版本"""
        logger.info(
            f"[Agent] 开始处理对话, user_id={user_id}, message={message}, session_id={session_id}"
        )

        session = await self._get_or_create_session(user_id, session_id)
        logger.info(f"[Agent] 会话ID: {session.session_id}")

        self._current_session = session

        _, context_hint, should_clear_disambiguation, should_clear_pending, skip_user_message = _preprocess_user_message(
            session, message
        )
        if context_hint:
            logger.info(f"[Agent] 上下文提示: {context_hint[:100]}...")
        if should_clear_disambiguation:
            await self.clear_disambiguation_context(session)
        if should_clear_pending:
            await self.clear_pending_confirmation(session)

        agent_graph = self.create_agent_graph(user_id)

        # 构建消息列表
        messages = self._build_chat_history(session)

        # 消歧处理完成后，只发送 context_hint，不添加假消息和原始用户消息
        if context_hint:
            if skip_user_message:
                messages.append(HumanMessage(content=context_hint))
            else:
                messages.append(HumanMessage(content=context_hint))
                messages.append(AIMessage(content="我理解了，会按照提示处理。"))
                messages.append(HumanMessage(content=message))
        else:
            messages.append(HumanMessage(content=message))

        try:
            logger.info("[Agent] 开始执行 agent.invoke")

            # LangChain 1.x 使用 messages 格式
            result = await agent_graph.ainvoke({"messages": messages})

            # 提取最终回复
            reply = ""
            actions = []

            result_messages = result.get("messages", [])
            for msg in result_messages:
                if isinstance(msg, AIMessage) and msg.content:
                    reply = msg.content
                elif isinstance(msg, ToolMessage):
                    # 记录工具调用结果
                    tool_name = getattr(msg, "name", "unknown")
                    actions.append({
                        "tool": tool_name,
                        "args": {},
                        "result": str(msg.content)[:200] if msg.content else None,
                        "status": "success",
                    })

            logger.info(f"[Agent] Agent 执行完成, reply={reply[:100] if reply else 'empty'}...")

            await self._update_session(session, message, reply)

            return {
                "session_id": session.session_id,
                "reply": reply,
                "actions": actions if actions else None,
                "reasoning": None,
                "requires_confirmation": False,
            }

        except Exception as e:
            logger.error(f"[Agent] 执行异常: {e}", exc_info=True)
            return {
                "session_id": session.session_id,
                "reply": f"处理请求时发生错误: {str(e)}",
                "actions": None,
                "reasoning": None,
                "requires_confirmation": False,
            }

    async def stream_chat(
        self, user_id: int, message: str, session_id: str | None = None
    ) -> AsyncGenerator[dict[str, Any], None]:
        """流式处理对话 - LangChain 1.x 版本"""
        session = await self._get_or_create_session(user_id, session_id)

        self._current_session = session

        _, context_hint, should_clear_disambiguation, should_clear_pending, skip_user_message = _preprocess_user_message(
            session, message
        )
        if context_hint:
            logger.info(f"[Agent Stream] 上下文提示: {context_hint[:100]}...")
        if should_clear_disambiguation:
            await self.clear_disambiguation_context(session)
        if should_clear_pending:
            await self.clear_pending_confirmation(session)

        yield {
            "type": "session",
            "session_id": session.session_id,
        }

        agent_graph = self.create_agent_graph(user_id)

        # 构建消息列表
        messages = self._build_chat_history(session)

        # 消歧处理完成后，只发送 context_hint，不添加假消息和原始用户消息
        # 这样 LLM 能准确理解要执行的操作
        if context_hint:
            if skip_user_message:
                # 消歧完成，直接发送指令让 LLM 执行
                messages.append(HumanMessage(content=context_hint))
            else:
                # 其他情况（如确认回复），保持原有消息结构
                messages.append(HumanMessage(content=context_hint))
                messages.append(AIMessage(content="我理解了，会按照提示处理。"))
                messages.append(HumanMessage(content=message))
        else:
            # 无特殊上下文，添加当前用户消息
            messages.append(HumanMessage(content=message))

        try:
            full_reply = ""
            actions = []
            should_stop = False

            logger.info(
                f"[Agent Stream] 开始执行, user_id={user_id}, message={message}"
            )

            # LangChain 1.x 使用 stream 方法，stream_mode=["messages", "updates"]
            async for stream_mode, data in agent_graph.astream(
                {"messages": messages},
                stream_mode=["messages", "updates"],
            ):
                # 检查是否需要中断（消歧或确认请求）
                if should_stop:
                    logger.info("[Agent Stream] 检测到需要用户交互，中断执行")
                    break

                if stream_mode == "messages":
                    token, _ = data
                    # LangGraph 的 astream 可能返回 AIMessage（完整消息）或 AIMessageChunk（流式块）
                    # AIMessageChunk 是 AIMessage 的子类，所以检查 AIMessage 可以同时处理两种情况
                    if isinstance(token, AIMessage):
                        # 处理流式文本或完整消息
                        if token.content:
                            full_reply += token.content
                            yield {
                                "type": "token",
                                "session_id": session.session_id,
                                "content": token.content,
                            }
                        # 处理工具调用块（仅 AIMessageChunk 有 tool_call_chunks）
                        if hasattr(token, "tool_call_chunks") and token.tool_call_chunks:
                            for tc in token.tool_call_chunks:
                                if tc.get("name"):
                                    logger.info(f"[Agent Tool] 调用开始: {tc['name']}")
                                    yield {
                                        "type": "action_start",
                                        "session_id": session.session_id,
                                        "action": {
                                            "tool": tc["name"],
                                            "args": tc.get("args", {}),
                                            "status": "running",
                                            "started_at": datetime.now().isoformat(),
                                        },
                                    }

                elif stream_mode == "updates":
                    for source, update in data.items():
                        if source == "tools" and update.get("messages"):
                            # 处理工具返回
                            tool_msg = update["messages"][-1]
                            if isinstance(tool_msg, ToolMessage):
                                tool_name = getattr(tool_msg, "name", "unknown")
                                tool_output = tool_msg.content
                                tool_input = tool_msg.tool_call_id or {}

                                logger.info(
                                    f"[Agent Tool] 调用完成: tool={tool_name}, result={str(tool_output)[:200]}"
                                )

                                output_str = str(tool_output) if tool_output else ""
                                action_status = "success"

                                if output_str.startswith("DISAMBIGUATION_REQUIRED"):
                                    logger.info("[Agent Stream] 检测到消歧请求，设置中断标志")
                                    pending_user_action = output_str.replace(
                                        "DISAMBIGUATION_REQUIRED\n\n", ""
                                    ).replace("DISAMBIGUATION_REQUIRED\n", "")
                                    if "【重要】" in pending_user_action:
                                        pending_user_action = pending_user_action.split("【重要】")[0].strip()
                                    full_reply = pending_user_action
                                    action_status = "pending"
                                    should_stop = True
                                elif output_str.startswith("CONFIRMATION_REQUIRED"):
                                    logger.info("[Agent Stream] 检测到确认请求，设置中断标志")
                                    pending_user_action = output_str.replace(
                                        "CONFIRMATION_REQUIRED\n\n", ""
                                    ).replace("CONFIRMATION_REQUIRED\n", "")
                                    if "【重要】" in pending_user_action:
                                        pending_user_action = pending_user_action.split("【重要】")[0].strip()
                                    full_reply = pending_user_action
                                    action_status = "pending"
                                    should_stop = True

                                parsed_data = None
                                parsed_message = str(tool_output)[:200] if tool_output else None
                                command_log_id = None

                                if tool_output:
                                    try:
                                        parsed = json.loads(tool_output)
                                        parsed_data = parsed.get("data")
                                        parsed_message = parsed.get("message", parsed_message)
                                        command_log_id = parsed.get("command_log_id")
                                        if parsed.get("status") == "failed":
                                            action_status = "failed"
                                    except (json.JSONDecodeError, TypeError):
                                        pass

                                actions.append({
                                    "tool": tool_name,
                                    "args": tool_input if isinstance(tool_input, dict) else {},
                                    "result": parsed_message,
                                    "status": action_status,
                                    "data": parsed_data,
                                    "command_log_id": command_log_id,
                                })

                                yield {
                                    "type": "action_end",
                                    "session_id": session.session_id,
                                    "action": {
                                        "tool": tool_name,
                                        "args": tool_input if isinstance(tool_input, dict) else {},
                                        "result": parsed_message,
                                        "status": action_status,
                                        "data": parsed_data,
                                        "command_log_id": command_log_id,
                                    },
                                }

                        elif source == "model" and update.get("messages"):
                            # 处理 AI 回复完成
                            ai_msg = update["messages"][-1]
                            if isinstance(ai_msg, AIMessage) and ai_msg.tool_calls:
                                # 记录工具调用
                                for tc in ai_msg.tool_calls:
                                    logger.info(f"[Agent Tool] 工具调用: {tc}")

            await self._update_session(session, message, full_reply)
            logger.info(
                f"[Agent Stream] 执行完成, actions={len(actions)}, reply_length={len(full_reply)}"
            )

            yield {
                "type": "done",
                "session_id": session.session_id,
                "reply": full_reply,
                "actions": actions if actions else None,
            }

        except Exception as e:
            logger.error(f"[Agent Stream] 执行异常: {e}", exc_info=True)
            yield {
                "type": "error",
                "session_id": session.session_id,
                "error": str(e),
            }

    def cleanup_expired_sessions(self):
        """清理过期会话"""
        cutoff_time = datetime.now() - timedelta(
            minutes=self._config.get("modbus_llm_session_ttl_minutes", 10)
        )

        stmt = select(AgentSessionModel).where(
            AgentSessionModel.last_active < cutoff_time
        )
        expired = self.db.execute(stmt).scalars().all()

        for session in expired:
            self.db.delete(session)

        self.db.commit()
        logger.info(f"已清理 {len(expired)} 个过期会话")

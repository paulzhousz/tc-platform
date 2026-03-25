"""
Modbus PLC 控制 API 控制器

提供设备连接、对话控制、直接读写等接口。
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import delete, select

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import ErrorResponse, SuccessResponse
from app.config.setting import settings
from app.core.dependencies import AuthPermission
from app.core.logger import log
from app.core.router_class import OperationLogRoute
from app.plugin.module_modbus.control.services.agent_service import AgentService
from app.plugin.module_modbus.control.services.connection_pool import connection_pool
from app.plugin.module_modbus.control.services.plc_service import PLCService
from app.plugin.module_modbus.models import ChatHistoryModel, DeviceModel
from app.plugin.module_modbus.schemas import (
    ChatHistoryCreate,
    ChatHistoryDetailResponse,
    ChatHistoryListResponse,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    ReadRequest,
    WriteRequest,
)

logger = logging.getLogger(__name__)

ControlRouter = APIRouter(
    route_class=OperationLogRoute, prefix="/control", tags=["Modbus控制操作"]
)

# 快捷指令配置文件路径
QUICK_COMMANDS_CONFIG_PATH = (
    Path(__file__).parent.parent.parent.parent / "config" / "modbus_quick_commands.json"
)


# ==================== 设备连接管理 ====================


@ControlRouter.post(
    "/connect",
    summary="连接设备",
    description="连接指定设备或所有活跃设备",
)
async def connect_devices(
    device_ids: Annotated[list[int] | None, Body(description="设备ID列表")] = None,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:write"]))],
) -> JSONResponse:
    """连接设备"""
    stmt = select(DeviceModel).where(DeviceModel.is_active == True)
    if device_ids:
        stmt = stmt.where(DeviceModel.id.in_(device_ids))

    devices = (await auth.db.execute(stmt)).scalars().all()
    if not devices:
        return ErrorResponse(msg="没有可连接的设备")

    results = []
    for device in devices:
        try:
            connection_pool.add_device(device)
            device.status = "online"
            device.last_seen = datetime.now(timezone.utc)
            results.append({
                "device_id": device.id,
                "device_name": device.name,
                "success": True,
            })
        except ConnectionError as e:
            device.status = "offline"
            results.append({
                "device_id": device.id,
                "device_name": device.name,
                "success": False,
                "error": str(e),
            })
        except Exception as e:
            device.status = "error"
            results.append({
                "device_id": device.id,
                "device_name": device.name,
                "success": False,
                "error": str(e),
            })

    await auth.db.commit()

    connected_count = sum(1 for r in results if r["success"])

    # 如果有设备连接成功，启动轮询服务
    if connected_count > 0 and settings.MODBUS_POLL_ENABLED:
        from app.plugin.module_modbus.control.services.poll_service import (
            poll_service,
        )

        if not poll_service._running:
            poll_service.start()

    if connected_count == 0:
        if len(devices) == 1:
            first_result = results[0]
            error_msg = first_result.get("error", "设备连接失败")
            return ErrorResponse(msg=error_msg, data={"results": results})
        else:
            return ErrorResponse(
                msg="所有设备连接失败，请确认设备已启动!", data={"results": results}
            )
    elif connected_count < len(devices):
        return SuccessResponse(
            data={
                "message": f"部分设备连接成功: {connected_count}/{len(devices)}",
                "results": results,
            },
            msg="部分设备连接成功",
        )
    else:
        return SuccessResponse(
            data={
                "message": f"已成功连接所有 {connected_count} 个设备",
                "results": results,
            },
            msg="连接成功",
        )


@ControlRouter.post(
    "/disconnect",
    summary="断开设备连接",
    description="断开指定设备或所有设备",
)
async def disconnect_devices(
    device_ids: Annotated[list[int] | None, Body(description="设备ID列表")] = None,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:write"]))],
) -> JSONResponse:
    """断开设备连接"""
    if device_ids:
        for device_id in device_ids:
            connection_pool.remove_device(device_id)
            stmt = select(DeviceModel).where(DeviceModel.id == device_id)
            device = (await auth.db.execute(stmt)).scalar_one_or_none()
            if device:
                device.status = "offline"
        await auth.db.commit()
        return SuccessResponse(msg=f"已断开 {len(device_ids)} 个设备连接")
    else:
        # 断开所有设备，停止轮询服务
        if settings.MODBUS_POLL_ENABLED:
            from app.plugin.module_modbus.control.services.poll_service import (
                poll_service,
            )

            if poll_service._running:
                poll_service.stop()

        connection_pool.close_all()

        # 更新所有设备状态为离线
        stmt = select(DeviceModel)
        devices = (await auth.db.execute(stmt)).scalars().all()
        for device in devices:
            device.status = "offline"
        await auth.db.commit()

        return SuccessResponse(msg="已断开所有设备连接")


@ControlRouter.get(
    "/connection-status",
    summary="获取连接状态",
    description="获取所有设备的连接状态",
)
async def get_connection_status(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:query"]))],
) -> JSONResponse:
    """获取设备连接状态"""
    stmt = select(DeviceModel).where(DeviceModel.is_active == True)
    devices = (await auth.db.execute(stmt)).scalars().all()

    results = []
    for device in devices:
        health = connection_pool.health_check(device.id)
        results.append({
            "device_id": device.id,
            "device_name": device.name,
            "status": device.status,
            "connected": health.get("healthy", False),
            "available_connections": health.get("available_connections", 0),
            "max_connections": health.get("max_connections", 0),
        })

    return SuccessResponse(data=results, msg="获取连接状态成功")


# ==================== 对话控制 ====================


@ControlRouter.post(
    "/chat",
    summary="对话接口",
    description="通过自然语言控制设备（同步）",
    response_model=ChatResponse,
)
async def chat(
    data: ChatRequest,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:write"]))],
) -> JSONResponse:
    """对话接口 - 通过自然语言控制设备"""
    agent_service = AgentService(auth.db)

    result = await agent_service.chat(
        user_id=auth.user.id,
        message=data.message,
        session_id=data.session_id,
    )

    return SuccessResponse(data=ChatResponse(**result), msg="对话处理完成")


@ControlRouter.post(
    "/chat/stream",
    summary="流式对话接口",
    description="通过自然语言控制设备（SSE 流式）",
)
async def chat_stream(
    data: ChatRequest,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:write"]))],
) -> StreamingResponse:
    """流式对话接口 - 使用 SSE 返回流式响应"""
    agent_service = AgentService(auth.db)

    async def generate():
        async for event in agent_service.stream_chat(
            user_id=auth.user.id,
            message=data.message,
            session_id=data.session_id,
        ):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ==================== 直接读写操作 ====================


@ControlRouter.post(
    "/read",
    summary="直接读取",
    description="直接读取 PLC 点位值（不经过 LLM）",
)
async def read_plc(
    data: ReadRequest,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:read"]))],
) -> JSONResponse:
    """直接读取 PLC 点位值"""
    plc_service = PLCService(auth.db)

    result = await plc_service.read(
        device_id=data.device_id,
        tag_code=data.tag_name,
        user_id=auth.user.id,
    )

    if not result["success"]:
        return ErrorResponse(msg=result["message"])

    return SuccessResponse(
        data={
            "device_id": data.device_id,
            "tag_name": data.tag_name,
            "value": result["value"],
            "raw_value": result["raw_value"],
            "unit": result.get("unit"),
        },
        msg="读取成功",
    )


@ControlRouter.post(
    "/write",
    summary="直接写入",
    description="直接写入 PLC 点位值（不经过 LLM）",
)
async def write_plc(
    data: WriteRequest,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:write"]))],
) -> JSONResponse:
    """直接写入 PLC 点位值"""
    plc_service = PLCService(auth.db)

    result = await plc_service.write(
        device_id=data.device_id,
        tag_code=data.tag_name,
        value=data.value,
        user_id=auth.user.id,
    )

    if result.get("requires_confirmation"):
        return SuccessResponse(
            data={
                "success": False,
                "requires_confirmation": True,
                "pending_confirm_id": result.get("pending_confirm_id"),
                "message": result["message"],
            },
            msg="操作需要确认",
        )

    if not result["success"]:
        return ErrorResponse(msg=result["message"])

    return SuccessResponse(
        data={
            "device_id": data.device_id,
            "tag_name": data.tag_name,
            "value": result["value"],
            "unit": result.get("unit"),
            "message": result["message"],
        },
        msg="写入成功",
    )


# ==================== 快捷指令 ====================


@ControlRouter.get(
    "/quick-commands",
    summary="获取快捷指令",
    description="获取快捷指令配置",
)
async def get_quick_commands(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:query"]))],
) -> JSONResponse:
    """获取快捷指令配置"""
    try:
        if not QUICK_COMMANDS_CONFIG_PATH.exists():
            return SuccessResponse(data={"quick_commands": []}, msg="获取成功")

        with open(QUICK_COMMANDS_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)

        return SuccessResponse(data=config, msg="获取成功")
    except json.JSONDecodeError as e:
        return ErrorResponse(msg=f"配置文件格式错误: {str(e)}")
    except Exception as e:
        return ErrorResponse(msg=f"读取配置文件失败: {str(e)}")


# ==================== 聊天历史 ====================


@ControlRouter.get(
    "/chat-history",
    summary="获取聊天历史列表",
    description="获取当前用户的聊天历史列表",
    response_model=ChatHistoryListResponse,
)
async def get_chat_history_list(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:query"]))],
    page: int = 1,
    page_size: int = 20,
) -> JSONResponse:
    """获取当前用户的聊天历史列表"""
    offset = (page - 1) * page_size

    stmt = select(ChatHistoryModel).where(ChatHistoryModel.user_id == auth.user.id)
    # 获取总数
    total_stmt = select(ChatHistoryModel.id).where(ChatHistoryModel.user_id == auth.user.id)
    total_result = await auth.db.execute(total_stmt)
    total = len(total_result.all())

    # 分页查询
    stmt = stmt.order_by(ChatHistoryModel.created_at.desc()).offset(offset).limit(page_size)
    histories = (await auth.db.execute(stmt)).scalars().all()

    items = [
        ChatHistoryResponse(
            id=h.id,
            session_id=h.session_id,
            title=h.title,
            device_count=h.device_count,
            device_names=h.device_names or [],
            start_time=h.start_time,
            end_time=h.end_time,
            created_at=h.created_at,
        )
        for h in histories
    ]

    return SuccessResponse(
        data=ChatHistoryListResponse(items=items, total=total), msg="获取成功"
    )


@ControlRouter.get(
    "/chat-history/{session_id}",
    summary="获取聊天历史详情",
    description="获取特定会话的聊天历史详情",
    response_model=ChatHistoryDetailResponse,
)
async def get_chat_history_detail(
    session_id: Annotated[str, Path(description="会话ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:query"]))],
) -> JSONResponse:
    """获取特定会话的聊天历史详情"""
    stmt = select(ChatHistoryModel).where(
        ChatHistoryModel.session_id == session_id,
        ChatHistoryModel.user_id == auth.user.id,
    )
    history = (await auth.db.execute(stmt)).scalar_one_or_none()

    if not history:
        return ErrorResponse(msg="聊天历史不存在")

    return SuccessResponse(
        data=ChatHistoryDetailResponse(
            id=history.id,
            session_id=history.session_id,
            title=history.title,
            device_count=history.device_count,
            device_names=history.device_names or [],
            start_time=history.start_time,
            end_time=history.end_time,
            created_at=history.created_at,
            messages=history.messages or [],
        ),
        msg="获取成功",
    )


@ControlRouter.post(
    "/chat-history",
    summary="保存聊天历史",
    description="保存当前会话的聊天历史",
)
async def save_chat_history(
    data: ChatHistoryCreate,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:write"]))],
) -> JSONResponse:
    """保存聊天历史"""
    if not data.messages:
        return ErrorResponse(msg="消息列表不能为空")

    # 生成标题
    title = None
    for msg in data.messages:
        if msg.role == "user":
            title = msg.content[:50] + ("..." if len(msg.content) > 50 else "")
            break

    # 解析时间戳
    def parse_iso_timestamp(ts: str) -> datetime:
        if not ts:
            return datetime.now(timezone.utc)
        try:
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            return datetime.fromisoformat(ts)
        except Exception:
            return datetime.now(timezone.utc)

    start_time = (
        parse_iso_timestamp(data.messages[0].timestamp)
        if data.messages
        else datetime.now(timezone.utc)
    )
    end_time = (
        parse_iso_timestamp(data.messages[-1].timestamp)
        if data.messages
        else datetime.now(timezone.utc)
    )

    messages_data = [msg.model_dump() for msg in data.messages]

    history = ChatHistoryModel(
        user_id=auth.user.id,
        session_id=data.session_id,
        title=title,
        messages=messages_data,
        device_count=data.device_count,
        device_names=data.device_names,
        start_time=start_time,
        end_time=end_time,
    )

    auth.db.add(history)
    await auth.db.commit()
    await auth.db.refresh(history)

    return SuccessResponse(
        data={
            "id": history.id,
            "session_id": history.session_id,
        },
        msg="聊天历史已保存",
    )


@ControlRouter.delete(
    "/chat-history/{session_id}",
    summary="删除聊天历史",
    description="删除特定会话的聊天历史",
)
async def delete_chat_history(
    session_id: Annotated[str, Path(description="会话ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:write"]))],
) -> JSONResponse:
    """删除特定会话的聊天历史"""
    stmt = select(ChatHistoryModel).where(
        ChatHistoryModel.session_id == session_id,
        ChatHistoryModel.user_id == auth.user.id,
    )
    history = (await auth.db.execute(stmt)).scalar_one_or_none()

    if not history:
        return ErrorResponse(msg="聊天历史不存在")

    await auth.db.delete(history)
    await auth.db.commit()

    return SuccessResponse(msg="聊天历史已删除")


@ControlRouter.delete(
    "/chat-history",
    summary="清空聊天历史",
    description="清空当前用户的所有聊天历史",
)
async def clear_all_chat_history(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:write"]))],
) -> JSONResponse:
    """清空当前用户的所有聊天历史"""
    stmt = delete(ChatHistoryModel).where(ChatHistoryModel.user_id == auth.user.id)
    result = await auth.db.execute(stmt)
    await auth.db.commit()

    return SuccessResponse(msg=f"已清空 {result.rowcount} 条聊天历史")
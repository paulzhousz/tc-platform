"""
Modbus 控制模块 API 控制器

包含设备管理、PLC 控制、日志查询、待确认操作等所有 API。
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Path, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import ErrorResponse, SuccessResponse
from app.config.setting import settings
from app.core.dependencies import AuthPermission
from app.core.logger import log
from app.core.router_class import OperationLogRoute
from app.plugin.module_modbus.control.services.agent_service import AgentService
from app.plugin.module_modbus.control.services.connection_pool import connection_pool
from app.plugin.module_modbus.control.services.plc_service import PLCService
from app.plugin.module_modbus.models import (
    ChatHistoryModel,
    CommandLogModel,
    DeviceModel,
    PendingConfirmModel,
    TagPointModel,
)
from app.plugin.module_modbus.schemas import (
    ChatHistoryCreate,
    ChatHistoryDetailResponse,
    ChatHistoryListResponse,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    CommandLogListResponse,
    CommandLogResponse,
    ConfirmAction,
    DeviceCreate,
    DeviceListResponse,
    DeviceResponse,
    DeviceUpdate,
    PendingConfirmListResponse,
    PendingConfirmResponse,
    ReadRequest,
    TagPointCreate,
    TagPointListResponse,
    TagPointResponse,
    TagPointUpdate,
    WriteRequest,
)

logger = logging.getLogger(__name__)

# 快捷指令配置文件路径
QUICK_COMMANDS_CONFIG_PATH = (
    Path(__file__).parent.parent.parent.parent / "config" / "modbus_quick_commands.json"
)

# ==================== 设备管理路由 ====================

DeviceRouter = APIRouter(
    route_class=OperationLogRoute, prefix="/device", tags=["Modbus设备管理"]
)


@DeviceRouter.get(
    "/list",
    summary="获取设备列表",
    description="获取所有设备列表",
    response_model=DeviceListResponse,
)
async def list_devices(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:device:query"]))],
) -> JSONResponse:
    """获取设备列表"""
    stmt = select(DeviceModel).order_by(DeviceModel.created_at.desc())
    devices = (await auth.db.execute(stmt)).scalars().all()

    items = [DeviceResponse.model_validate(d) for d in devices]
    return SuccessResponse(
        data=DeviceListResponse(items=items, total=len(items)),
        msg="获取设备列表成功",
    )


@DeviceRouter.post(
    "/create",
    summary="创建设备",
    description="创建新设备",
    response_model=DeviceResponse,
)
async def create_device(
    data: DeviceCreate,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:device:create"]))],
) -> JSONResponse:
    """创建设备"""
    stmt = select(DeviceModel).where(DeviceModel.code == data.code)
    existing = (await auth.db.execute(stmt)).scalar_one_or_none()
    if existing:
        return ErrorResponse(msg=f"设备编码 '{data.code}' 已存在")

    device = DeviceModel(**data.model_dump())
    auth.db.add(device)
    await auth.db.commit()
    await auth.db.refresh(device)

    try:
        connection_pool.add_device(device)
    except Exception as e:
        log.warning(f"设备添加到连接池失败: {e}")

    log.info(f"创建设备成功: {device.name}")
    return SuccessResponse(data=DeviceResponse.model_validate(device), msg="创建设备成功")


@DeviceRouter.get(
    "/detail/{id}",
    summary="获取设备详情",
    description="获取设备详情",
    response_model=DeviceResponse,
)
async def get_device(
    id: Annotated[int, Path(description="设备ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:device:detail"]))],
) -> JSONResponse:
    """获取设备详情"""
    stmt = select(DeviceModel).where(DeviceModel.id == id)
    device = (await auth.db.execute(stmt)).scalar_one_or_none()
    if not device:
        return ErrorResponse(msg="设备不存在")

    return SuccessResponse(data=DeviceResponse.model_validate(device), msg="获取设备详情成功")


@DeviceRouter.put(
    "/update/{id}",
    summary="更新设备",
    description="更新设备信息",
    response_model=DeviceResponse,
)
async def update_device(
    id: Annotated[int, Path(description="设备ID")],
    data: DeviceUpdate,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:device:update"]))],
) -> JSONResponse:
    """更新设备"""
    stmt = select(DeviceModel).where(DeviceModel.id == id)
    device = (await auth.db.execute(stmt)).scalar_one_or_none()
    if not device:
        return ErrorResponse(msg="设备不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(device, key, value)

    await auth.db.commit()
    await auth.db.refresh(device)

    connection_pool.remove_device(id)
    try:
        connection_pool.add_device(device)
    except Exception as e:
        log.warning(f"设备重新添加到连接池失败: {e}")

    log.info(f"更新设备成功: {device.name}")
    return SuccessResponse(data=DeviceResponse.model_validate(device), msg="更新设备成功")


@DeviceRouter.delete(
    "/delete",
    summary="删除设备",
    description="删除设备",
)
async def delete_device(
    ids: Annotated[list[int], Body(description="设备ID列表")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:device:delete"]))],
) -> JSONResponse:
    """删除设备"""
    for device_id in ids:
        stmt = select(DeviceModel).where(DeviceModel.id == device_id)
        device = (await auth.db.execute(stmt)).scalar_one_or_none()
        if device:
            connection_pool.remove_device(device_id)
            await auth.db.delete(device)

    await auth.db.commit()
    log.info(f"删除设备成功: {ids}")
    return SuccessResponse(msg="删除设备成功")


@DeviceRouter.post(
    "/{id}/test",
    summary="测试设备连接",
    description="测试设备连接是否正常",
)
async def test_device_connection(
    id: Annotated[int, Path(description="设备ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:device:detail"]))],
) -> JSONResponse:
    """测试设备连接"""
    stmt = select(DeviceModel).where(DeviceModel.id == id)
    device = (await auth.db.execute(stmt)).scalar_one_or_none()
    if not device:
        return ErrorResponse(msg="设备不存在")

    client = connection_pool.acquire(id)
    if not client:
        return SuccessResponse(
            data={"connected": False, "message": "无法获取连接"},
            msg="连接测试失败",
        )

    try:
        result = client.read_holding_registers(0, 1, slave=device.slave_id)
        if result.get("success"):
            return SuccessResponse(
                data={"connected": True, "message": "连接正常"},
                msg="连接测试成功",
            )
        else:
            return SuccessResponse(
                data={"connected": False, "message": result.get("error", "读取失败")},
                msg="连接测试失败",
            )
    except Exception as e:
        return SuccessResponse(
            data={"connected": False, "message": str(e)},
            msg="连接测试失败",
        )
    finally:
        connection_pool.release(id, client)


# ==================== 点位管理 ====================


@DeviceRouter.get(
    "/{device_id}/tag/list",
    summary="获取点位列表",
    description="获取设备的点位列表",
    response_model=TagPointListResponse,
)
async def list_tags(
    device_id: Annotated[int, Path(description="设备ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:tag:query"]))],
) -> JSONResponse:
    """获取设备的点位列表"""
    stmt = (
        select(TagPointModel)
        .where(TagPointModel.device_id == device_id)
        .order_by(TagPointModel.sort_order, TagPointModel.id)
    )
    tags = (await auth.db.execute(stmt)).scalars().all()

    items = [TagPointResponse.model_validate(t) for t in tags]
    return SuccessResponse(
        data=TagPointListResponse(items=items, total=len(items)),
        msg="获取点位列表成功",
    )


@DeviceRouter.post(
    "/{device_id}/tag/create",
    summary="创建点位",
    description="创建新点位",
    response_model=TagPointResponse,
)
async def create_tag(
    device_id: Annotated[int, Path(description="设备ID")],
    data: TagPointCreate,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:tag:create"]))],
) -> JSONResponse:
    """创建点位"""
    stmt = select(DeviceModel).where(DeviceModel.id == device_id)
    device = (await auth.db.execute(stmt)).scalar_one_or_none()
    if not device:
        return ErrorResponse(msg="设备不存在")

    stmt = select(TagPointModel).where(
        TagPointModel.device_id == device_id, TagPointModel.code == data.code
    )
    existing = (await auth.db.execute(stmt)).scalar_one_or_none()
    if existing:
        return ErrorResponse(msg=f"点位编码 '{data.code}' 已存在")

    tag = TagPointModel(**data.model_dump(), device_id=device_id)
    auth.db.add(tag)
    await auth.db.commit()
    await auth.db.refresh(tag)

    log.info(f"创建点位成功: {tag.name}")
    return SuccessResponse(data=TagPointResponse.model_validate(tag), msg="创建点位成功")


@DeviceRouter.put(
    "/tag/update/{tag_id}",
    summary="更新点位",
    description="更新点位信息",
    response_model=TagPointResponse,
)
async def update_tag(
    tag_id: Annotated[int, Path(description="点位ID")],
    data: TagPointUpdate,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:tag:update"]))],
) -> JSONResponse:
    """更新点位"""
    stmt = select(TagPointModel).where(TagPointModel.id == tag_id)
    tag = (await auth.db.execute(stmt)).scalar_one_or_none()
    if not tag:
        return ErrorResponse(msg="点位不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tag, key, value)

    await auth.db.commit()
    await auth.db.refresh(tag)

    log.info(f"更新点位成功: {tag.name}")
    return SuccessResponse(data=TagPointResponse.model_validate(tag), msg="更新点位成功")


@DeviceRouter.delete(
    "/tag/delete",
    summary="删除点位",
    description="删除点位",
)
async def delete_tag(
    ids: Annotated[list[int], Body(description="点位ID列表")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:tag:delete"]))],
) -> JSONResponse:
    """删除点位"""
    for tag_id in ids:
        stmt = select(TagPointModel).where(TagPointModel.id == tag_id)
        tag = (await auth.db.execute(stmt)).scalar_one_or_none()
        if tag:
            await auth.db.delete(tag)

    await auth.db.commit()
    log.info(f"删除点位成功: {ids}")
    return SuccessResponse(msg="删除点位成功")


# ==================== PLC 控制路由 ====================

ControlRouter = APIRouter(
    route_class=OperationLogRoute, prefix="/control", tags=["Modbus控制操作"]
)


@ControlRouter.post(
    "/connect",
    summary="连接设备",
    description="连接指定设备或所有活跃设备",
)
async def connect_devices(
    device_ids: Annotated[list[int] | None, Body(description="设备ID列表")] = None,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:write"]))] = None,
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
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:write"]))] = None,
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
        if settings.MODBUS_POLL_ENABLED:
            from app.plugin.module_modbus.control.services.poll_service import (
                poll_service,
            )

            if poll_service._running:
                poll_service.stop()

        connection_pool.close_all()

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
    page: Annotated[int, Query(ge=1, description="页码")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="每页数量")] = 20,
) -> JSONResponse:
    """获取当前用户的聊天历史列表"""
    offset = (page - 1) * page_size

    stmt = select(ChatHistoryModel).where(ChatHistoryModel.user_id == auth.user.id)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await auth.db.execute(count_stmt)).scalar() or 0

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

    title = None
    for msg in data.messages:
        if msg.role == "user":
            title = msg.content[:50] + ("..." if len(msg.content) > 50 else "")
            break

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


# ==================== 操作日志路由 ====================

LogRouter = APIRouter(
    route_class=OperationLogRoute, prefix="/log", tags=["Modbus操作日志"]
)


@LogRouter.get(
    "/list",
    summary="获取操作日志列表",
    description="获取操作日志列表（支持筛选和分页）",
    response_model=CommandLogListResponse,
)
async def list_logs(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:log:query"]))],
    device_id: Annotated[int | None, Query(description="设备ID筛选")] = None,
    user_id: Annotated[int | None, Query(description="用户ID筛选")] = None,
    action: Annotated[str | None, Query(description="操作类型筛选")] = None,
    status: Annotated[str | None, Query(description="状态筛选")] = None,
    start_time: Annotated[datetime | None, Query(description="开始时间")] = None,
    end_time: Annotated[datetime | None, Query(description="结束时间")] = None,
    page: Annotated[int, Query(ge=1, description="页码")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="每页数量")] = 20,
) -> JSONResponse:
    """获取操作日志列表"""
    stmt = select(CommandLogModel)

    if device_id:
        stmt = stmt.where(CommandLogModel.device_id == device_id)
    if user_id:
        stmt = stmt.where(CommandLogModel.user_id == user_id)
    if action:
        stmt = stmt.where(CommandLogModel.action == action)
    if status:
        stmt = stmt.where(CommandLogModel.status == status)
    if start_time:
        stmt = stmt.where(CommandLogModel.created_at >= start_time)
    if end_time:
        stmt = stmt.where(CommandLogModel.created_at <= end_time)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await auth.db.execute(count_stmt)).scalar() or 0

    offset = (page - 1) * page_size
    stmt = stmt.order_by(CommandLogModel.created_at.desc()).offset(offset).limit(page_size)
    logs = (await auth.db.execute(stmt)).scalars().all()

    items = [CommandLogResponse.model_validate(log) for log in logs]
    return SuccessResponse(
        data=CommandLogListResponse(items=items, total=total), msg="获取成功"
    )


@LogRouter.get(
    "/detail/{id}",
    summary="获取操作日志详情",
    description="获取操作日志详情",
    response_model=CommandLogResponse,
)
async def get_log(
    id: Annotated[int, Path(description="日志ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:log:detail"]))],
) -> JSONResponse:
    """获取操作日志详情"""
    stmt = select(CommandLogModel).where(CommandLogModel.id == id)
    log_entry = (await auth.db.execute(stmt)).scalar_one_or_none()

    if not log_entry:
        return ErrorResponse(msg="日志不存在")

    return SuccessResponse(data=CommandLogResponse.model_validate(log_entry), msg="获取成功")


# ==================== 待确认操作路由 ====================

PendingRouter = APIRouter(
    route_class=OperationLogRoute, prefix="/pending", tags=["Modbus待确认操作"]
)


@PendingRouter.get(
    "/list",
    summary="获取待确认操作列表",
    description="获取待确认操作列表",
    response_model=PendingConfirmListResponse,
)
async def list_pending(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:write"]))],
    status: Annotated[str | None, Query(description="状态筛选")] = None,
) -> JSONResponse:
    """获取待确认操作列表"""
    stmt = select(PendingConfirmModel)

    if status:
        stmt = stmt.where(PendingConfirmModel.status == status)
    else:
        stmt = stmt.where(PendingConfirmModel.status == "pending")

    stmt = stmt.order_by(PendingConfirmModel.created_at.desc())
    pendings = (await auth.db.execute(stmt)).scalars().all()

    items = [PendingConfirmResponse.model_validate(p) for p in pendings]
    return SuccessResponse(
        data=PendingConfirmListResponse(items=items, total=len(items)), msg="获取成功"
    )


@PendingRouter.post(
    "/{pending_id}/confirm",
    summary="确认操作",
    description="确认执行待确认操作",
)
async def confirm_operation(
    pending_id: Annotated[int, Path(description="待确认ID")],
    data: ConfirmAction,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:write"]))],
) -> JSONResponse:
    """确认操作"""
    stmt = select(PendingConfirmModel).where(PendingConfirmModel.id == pending_id)
    pending = (await auth.db.execute(stmt)).scalar_one_or_none()

    if not pending:
        return ErrorResponse(msg="待确认记录不存在")

    if pending.status != "pending":
        return ErrorResponse(msg=f"该操作已处理，状态: {pending.status}")

    if pending.expires_at and datetime.now() > pending.expires_at:
        pending.status = "expired"
        await auth.db.commit()
        return ErrorResponse(msg="操作已过期")

    stmt = select(DeviceModel).where(DeviceModel.name == pending.device_name)
    device = (await auth.db.execute(stmt)).scalar_one_or_none()
    if not device:
        return ErrorResponse(msg=f"设备 '{pending.device_name}' 不存在")

    stmt = select(TagPointModel).where(
        TagPointModel.device_id == device.id, TagPointModel.name == pending.tag_name
    )
    tag = (await auth.db.execute(stmt)).scalar_one_or_none()
    if not tag:
        return ErrorResponse(msg=f"点位 '{pending.tag_name}' 不存在")

    plc_service = PLCService(auth.db)
    result = await plc_service.write(
        device_id=device.id,
        tag_code=tag.code,
        value=pending.target_value,
        user_id=auth.user.id,
    )

    pending.status = "confirmed"
    pending.reviewed_by = auth.user.id
    pending.reviewed_at = datetime.now()
    pending.review_comment = data.comment
    await auth.db.commit()

    if result["success"]:
        return SuccessResponse(
            data={
                "message": "操作已确认并执行",
                "result": result,
            },
            msg="操作成功",
        )
    else:
        return ErrorResponse(msg=f"执行失败: {result['message']}")


@PendingRouter.post(
    "/{pending_id}/reject",
    summary="拒绝操作",
    description="拒绝执行待确认操作",
)
async def reject_operation(
    pending_id: Annotated[int, Path(description="待确认ID")],
    data: ConfirmAction,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:write"]))],
) -> JSONResponse:
    """拒绝操作"""
    stmt = select(PendingConfirmModel).where(PendingConfirmModel.id == pending_id)
    pending = (await auth.db.execute(stmt)).scalar_one_or_none()

    if not pending:
        return ErrorResponse(msg="待确认记录不存在")

    if pending.status != "pending":
        return ErrorResponse(msg=f"该操作已处理，状态: {pending.status}")

    pending.status = "rejected"
    pending.reviewed_by = auth.user.id
    pending.reviewed_at = datetime.now()
    pending.review_comment = data.comment
    await auth.db.commit()

    return SuccessResponse(msg="操作已拒绝")
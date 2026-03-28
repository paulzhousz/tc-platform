"""
Modbus 控制模块 API 控制器

包含设备管理、PLC 控制、日志查询、待确认操作等所有 API。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path as PathlibPath
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query
from fastapi.responses import JSONResponse, StreamingResponse
from redis.asyncio.client import Redis
from sqlalchemy import select

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import ErrorResponse, SuccessResponse
from app.core.dependencies import AuthPermission, redis_getter
from app.core.router_class import OperationLogRoute
from app.plugin.module_modbus.control.services.agent_service import AgentService
from app.plugin.module_modbus.control.services.chat_history_service import ChatHistoryService
from app.plugin.module_modbus.control.services.command_log_service import CommandLogService
from app.plugin.module_modbus.control.services.config_service import ModbusConfigService
from app.plugin.module_modbus.control.services.connection_pool import connection_pool
from app.plugin.module_modbus.control.services.pending_confirm_service import PendingConfirmService
from app.plugin.module_modbus.control.services.plc_service import PLCService
from app.plugin.module_modbus.control.services.websocket_service import ws_manager
from app.plugin.module_modbus.models import (
    DeviceModel,
)
from app.plugin.module_modbus.schemas import (
    ChatHistoryCreate,
    ChatHistoryDetailResponse,
    ChatHistoryListResponse,
    ChatRequest,
    ChatResponse,
    CommandLogFilter,
    CommandLogListResponse,
    CommandLogResponse,
    ConfirmAction,
    PendingConfirmListResponse,
    ReadRequest,
    WriteRequest,
)

logger = logging.getLogger(__name__)

# 快捷指令配置文件路径
# controller.py -> control -> module_modbus -> plugin -> app -> backend/
QUICK_COMMANDS_CONFIG_PATH = (
    PathlibPath(__file__).parent.parent.parent.parent.parent / "config" / "modbus_quick_commands.json"
)

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
    auth: AuthSchema = Depends(AuthPermission(["module_modbus:control:write"])),
    redis: Redis = Depends(redis_getter),
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
            device.device_status = "online"
            device.last_seen = datetime.now()
            results.append({
                "device_id": device.id,
                "device_name": device.name,
                "success": True,
            })
        except ConnectionError as e:
            device.device_status = "offline"
            results.append({
                "device_id": device.id,
                "device_name": device.name,
                "success": False,
                "error": str(e),
            })
        except Exception as e:
            device.device_status = "error"
            results.append({
                "device_id": device.id,
                "device_name": device.name,
                "success": False,
                "error": str(e),
            })

    await auth.db.flush()

    # 推送设备状态变化
    for device in devices:
        await ws_manager.send_device_status(
            device_id=device.id,
            device_name=device.name,
            status=device.device_status,
            last_seen=device.last_seen,
        )

    connected_count = sum(1 for r in results if r["success"])

    if connected_count > 0 and await ModbusConfigService.get(redis, "modbus_poll_enabled"):
        from app.plugin.module_modbus.control.services.poll_service import (
            poll_service,
        )

        if not poll_service._running:
            await poll_service.start(redis)

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
    auth: AuthSchema = Depends(AuthPermission(["module_modbus:control:write"])),
    redis: Redis = Depends(redis_getter),
) -> JSONResponse:
    """断开设备连接"""
    if device_ids:
        for device_id in device_ids:
            connection_pool.remove_device(device_id)
            stmt = select(DeviceModel).where(DeviceModel.id == device_id)
            device = (await auth.db.execute(stmt)).scalar_one_or_none()
            if device:
                device.device_status = "offline"
                await ws_manager.send_device_status(
                    device_id=device.id,
                    device_name=device.name,
                    status="offline",
                    last_seen=None,
                )
        await auth.db.flush()
        return SuccessResponse(msg=f"已断开 {len(device_ids)} 个设备连接")
    else:
        if await ModbusConfigService.get(redis, "modbus_poll_enabled"):
            from app.plugin.module_modbus.control.services.poll_service import (
                poll_service,
            )

            if poll_service._running:
                poll_service.stop()

        connection_pool.close_all()

        stmt = select(DeviceModel)
        devices = (await auth.db.execute(stmt)).scalars().all()
        for device in devices:
            device.device_status = "offline"
            await ws_manager.send_device_status(
                device_id=device.id,
                device_name=device.name,
                status="offline",
                last_seen=None,
            )
        await auth.db.flush()

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
            "status": device.device_status,
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
    redis: Redis = Depends(redis_getter),
) -> JSONResponse:
    """对话接口 - 通过自然语言控制设备"""
    config = await ModbusConfigService.get_all(redis)
    agent_service = AgentService(auth.db, config)

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
    redis: Redis = Depends(redis_getter),
) -> StreamingResponse:
    """流式对话接口 - 使用 SSE 返回流式响应"""
    config = await ModbusConfigService.get_all(redis)
    agent_service = AgentService(auth.db, config)

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
    redis: Redis = Depends(redis_getter),
) -> JSONResponse:
    """直接读取 PLC 点位值"""
    plc_service = PLCService(auth.db, redis)

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
    redis: Redis = Depends(redis_getter),
) -> JSONResponse:
    """直接写入 PLC 点位值"""
    plc_service = PLCService(auth.db, redis)

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

        with open(QUICK_COMMANDS_CONFIG_PATH, encoding="utf-8") as f:
            config = json.load(f)

        return SuccessResponse(data=config, msg="获取成功")
    except json.JSONDecodeError as e:
        return ErrorResponse(msg=f"配置文件格式错误: {str(e)}")
    except Exception as e:
        return ErrorResponse(msg=f"读取配置文件失败: {str(e)}")


@ControlRouter.get(
    "/config",
    summary="获取 Modbus 配置",
    description="获取 Modbus 控制模块的运行时配置（从 Redis 缓存获取）",
)
async def get_modbus_config(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:query"]))],
    redis: Redis = Depends(redis_getter),
) -> JSONResponse:
    """获取 Modbus 运行时配置"""
    config = await ModbusConfigService.get_all(redis)
    return SuccessResponse(data=config, msg="获取配置成功")


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
    service = ChatHistoryService(auth.db)
    result = await service.list(
        user_id=auth.user.id,
        page=page,
        page_size=page_size,
    )
    return SuccessResponse(data=result, msg="获取成功")


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
    service = ChatHistoryService(auth.db)
    result = await service.get_detail(session_id, auth.user.id)

    if not result:
        return ErrorResponse(msg="聊天历史不存在")

    return SuccessResponse(data=result, msg="获取成功")


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
    service = ChatHistoryService(auth.db)
    result = await service.create(user_id=auth.user.id, data=data)

    if not result.get("success"):
        return ErrorResponse(msg=result.get("message", "保存失败"))

    return SuccessResponse(
        data={"id": result["id"], "session_id": result["session_id"]},
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
    service = ChatHistoryService(auth.db)
    result = await service.delete(session_id, auth.user.id)

    if not result.get("success"):
        return ErrorResponse(msg=result.get("message", "删除失败"))

    return SuccessResponse(msg=result["message"])


@ControlRouter.delete(
    "/chat-history",
    summary="清空聊天历史",
    description="清空当前用户的所有聊天历史",
)
async def clear_all_chat_history(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:write"]))],
) -> JSONResponse:
    """清空当前用户的所有聊天历史"""
    service = ChatHistoryService(auth.db)
    result = await service.clear_all(auth.user.id)
    return SuccessResponse(msg=result["message"])


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
    filter_params = CommandLogFilter(
        device_id=device_id,
        user_id=user_id,
        action=action,
        status=status,
        start_time=start_time,
        end_time=end_time,
    )
    service = CommandLogService(auth.db)
    result = await service.list(filter_params=filter_params, page=page, page_size=page_size)
    return SuccessResponse(data=result, msg="获取成功")


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
    service = CommandLogService(auth.db)
    result = await service.get_detail(id)

    if not result:
        return ErrorResponse(msg="日志不存在")

    return SuccessResponse(data=result, msg="获取成功")


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
    service = PendingConfirmService(auth.db)
    result = await service.list(status=status)
    return SuccessResponse(data=result, msg="获取成功")


@PendingRouter.post(
    "/{pending_id}/confirm",
    summary="确认操作",
    description="确认执行待确认操作",
)
async def confirm_operation(
    pending_id: Annotated[int, Path(description="待确认ID")],
    data: ConfirmAction,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:write"]))],
    redis: Redis = Depends(redis_getter),
) -> JSONResponse:
    """确认操作"""
    service = PendingConfirmService(auth.db, redis)
    result = await service.confirm(
        pending_id=pending_id,
        user_id=auth.user.id,
        data=data,
    )

    if not result.get("success"):
        return ErrorResponse(msg=result.get("message", "确认失败"))

    return SuccessResponse(data=result, msg="操作成功")


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
    service = PendingConfirmService(auth.db)
    result = await service.reject(
        pending_id=pending_id,
        user_id=auth.user.id,
        data=data,
    )

    if not result.get("success"):
        return ErrorResponse(msg=result.get("message", "拒绝失败"))

    return SuccessResponse(msg=result["message"])

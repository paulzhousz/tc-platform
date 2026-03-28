"""
Modbus WebSocket 实时通信接口

功能：
- 设备状态实时推送
- 点位值变化实时推送
- 操作结果实时推送
- 待确认操作通知

连接地址: ws://127.0.0.1:9000/api/v1/ws/modbus?token=xxx

消息格式（服务端推送）:
- 设备状态: {"type": "device_status", "data": {...}}
- 点位值变化: {"type": "tag_value", "data": {...}}
- 操作结果: {"type": "operation_result", "data": {...}}
- 待确认通知: {"type": "pending_confirm", "data": {...}}

客户端消息:
- 心跳: {"type": "ping"}
"""

from fastapi import APIRouter, WebSocket

from app.core.database import async_db_session
from app.core.dependencies import _verify_token
from app.core.logger import log as logger
from app.core.router_class import OperationLogRoute

WSModbus = APIRouter(
    route_class=OperationLogRoute,
    prefix="/ws/modbus",
    tags=["Modbus WebSocket"],
)


@WSModbus.websocket("", name="Modbus实时通信")
async def websocket_modbus_controller(
    websocket: WebSocket,
) -> None:
    """
    Modbus WebSocket 实时通信接口
    """
    from app.plugin.module_modbus.control.services.websocket_service import (
        websocket_endpoint,
    )

    await websocket.accept()

    # 从查询参数获取token并认证
    token = websocket.query_params.get("token")
    if not token:
        logger.warning(f"WebSocket连接未提供token: {websocket.client}")
        try:
            await websocket.send_json({"type": "error", "message": "未提供认证token"})
        except RuntimeError:
            pass
        finally:
            try:
                await websocket.close()
            except RuntimeError:
                pass
        return

    try:
        async with async_db_session() as db:
            redis = websocket.app.state.redis
            auth = await _verify_token(token, db, redis)

            if not auth or not auth.user:
                logger.warning(f"WebSocket认证失败: {websocket.client}")
                try:
                    await websocket.send_json({"type": "error", "message": "认证失败"})
                except RuntimeError:
                    pass
                finally:
                    try:
                        await websocket.close()
                    except RuntimeError:
                        pass
                return

            logger.info(f"Modbus WebSocket已连接: {websocket.client} - 用户: {auth.user.username}")

            # 调用 WebSocket 端点处理
            await websocket_endpoint(websocket, auth.user.id)

    except Exception as e:
        logger.error(f"WebSocket异常: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except RuntimeError:
            pass
        finally:
            try:
                await websocket.close()
            except RuntimeError:
                pass

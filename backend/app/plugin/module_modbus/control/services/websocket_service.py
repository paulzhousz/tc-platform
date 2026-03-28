"""
WebSocket 推送服务

管理 WebSocket 连接，支持实时推送设备状态、点位变化等消息。
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # {user_id: Set[WebSocket]}
        self._connections: dict[int, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: int):
        """建立连接"""
        # 注意：websocket.accept() 已在控制器层调用，这里只负责连接管理

        async with self._lock:
            if user_id not in self._connections:
                self._connections[user_id] = set()
            self._connections[user_id].add(websocket)

        logger.info(f"用户 {user_id} WebSocket 已连接")

    async def disconnect(self, websocket: WebSocket, user_id: int):
        """断开连接"""
        async with self._lock:
            if user_id in self._connections:
                self._connections[user_id].discard(websocket)
                if not self._connections[user_id]:
                    del self._connections[user_id]

        logger.info(f"用户 {user_id} WebSocket 已断开")

    async def send_to_user(self, user_id: int, message: dict[str, Any]):
        """发送消息给指定用户"""
        async with self._lock:
            connections = self._connections.get(user_id, set()).copy()

        message["timestamp"] = datetime.now().isoformat()

        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                disconnected.append(websocket)

        # 清理断开的连接
        async with self._lock:
            for ws in disconnected:
                if user_id in self._connections:
                    self._connections[user_id].discard(ws)

    async def broadcast(self, message: dict[str, Any]):
        """广播消息给所有连接"""
        message["timestamp"] = datetime.now().isoformat()

        async with self._lock:
            all_connections = list(self._connections.items())

        for user_id, connections in all_connections:
            for websocket in connections.copy():
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"广播消息失败: {e}")

    async def send_device_status(
        self,
        device_id: int,
        device_name: str,
        status: str,
        last_seen: datetime | None = None,
    ):
        """发送设备状态变化"""
        message = {
            "type": "device_status",
            "data": {
                "device_id": device_id,
                "device_name": device_name,
                "status": status,
                "last_seen": last_seen.isoformat() if last_seen else None,
            },
        }
        await self.broadcast(message)

    async def send_tag_value(
        self,
        user_id: int,
        device_id: int,
        tag_id: int,
        tag_name: str,
        value: float,
        unit: str | None = None,
        previous_value: float | None = None,
    ):
        """发送点位值变化"""
        message = {
            "type": "tag_value",
            "data": {
                "device_id": device_id,
                "tag_id": tag_id,
                "tag_name": tag_name,
                "value": value,
                "unit": unit,
                "previous_value": previous_value,
            },
        }
        await self.send_to_user(user_id, message)

    async def send_operation_result(
        self, user_id: int, command_log_id: int, success: bool, message: str
    ):
        """发送操作结果"""
        msg = {
            "type": "operation_result",
            "data": {
                "command_log_id": command_log_id,
                "success": success,
                "message": message,
            },
        }
        await self.send_to_user(user_id, msg)

    async def send_pending_confirm(
        self,
        user_id: int,
        pending_id: int,
        device_name: str,
        tag_name: str,
        target_value: float,
        unit: str | None = None,
        user_input: str | None = None,
        expires_at: datetime | None = None,
    ):
        """发送待确认通知"""
        message = {
            "type": "pending_confirm",
            "data": {
                "pending_confirm_id": pending_id,
                "device_name": device_name,
                "tag_name": tag_name,
                "target_value": target_value,
                "unit": unit,
                "user_input": user_input,
                "expires_at": expires_at.isoformat() if expires_at else None,
            },
        }
        await self.send_to_user(user_id, message)


# 全局连接管理器
ws_manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """WebSocket 端点处理"""
    await ws_manager.connect(websocket, user_id)

    try:
        while True:
            # 接收客户端消息（心跳或其他指令）
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                # 处理心跳
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket 异常: {e}")
        await ws_manager.disconnect(websocket, user_id)

"""
Modbus 控制 API 测试

测试 ControlRouter 的所有端点。
"""

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock


API_PREFIX = "/api/v1/modbus/control"


class TestConnectAPI:
    """设备连接 API 测试"""

    def test_connect_all_devices_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_connection_pool,
        mock_device_model
    ):
        """测试连接所有设备 - 成功"""
        # Mock 查询返回活跃设备
        mock_auth._execute_result.scalars.return_value.all.return_value = [mock_device_model]

        response = client.post(f"{API_PREFIX}/connect")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "成功" in data["msg"]

    def test_connect_specific_devices(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_connection_pool,
        mock_device_model
    ):
        """测试连接指定设备"""
        mock_auth._execute_result.scalars.return_value.all.return_value = [mock_device_model]

        response = client.post(f"{API_PREFIX}/connect", json=[1, 2])

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    def test_connect_no_devices(self, client, mock_auth_dependency, mock_auth):
        """测试连接 - 没有可连接的设备"""
        # Mock 返回空列表
        mock_auth._execute_result.scalars.return_value.all.return_value = []

        response = client.post(f"{API_PREFIX}/connect")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] != 200
        assert "没有可连接" in data["msg"]

    def test_connect_partial_failure(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_connection_pool,
        mock_device_model
    ):
        """测试连接 - 部分设备连接失败"""
        mock_auth._execute_result.scalars.return_value.all.return_value = [mock_device_model]

        # Mock 连接池抛出异常
        mock_connection_pool.add_device.side_effect = ConnectionError("连接超时")

        response = client.post(f"{API_PREFIX}/connect")

        assert response.status_code == 200
        data = response.json()
        # 单设备连接失败返回错误
        assert data["code"] != 200


class TestDisconnectAPI:
    """设备断开 API 测试"""

    def test_disconnect_specific_devices(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_connection_pool,
        mock_device_model
    ):
        """测试断开指定设备"""
        mock_auth._execute_result.scalar_one_or_none.return_value = mock_device_model

        response = client.post(f"{API_PREFIX}/disconnect", json=[1, 2])

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "断开" in data["msg"]

    def test_disconnect_all_devices(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_connection_pool,
        mock_device_model
    ):
        """测试断开所有设备"""
        mock_auth._execute_result.scalars.return_value.all.return_value = [mock_device_model]

        response = client.post(f"{API_PREFIX}/disconnect")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "断开" in data["msg"]


class TestConnectionStatusAPI:
    """连接状态 API 测试"""

    def test_get_connection_status_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_connection_pool,
        mock_device_model
    ):
        """测试获取连接状态 - 成功"""
        mock_auth._execute_result.scalars.return_value.all.return_value = [mock_device_model]

        response = client.get(f"{API_PREFIX}/connection-status")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert isinstance(data["data"], list)

    def test_get_connection_status_empty(
        self,
        client,
        mock_auth_dependency,
        mock_auth
    ):
        """测试获取连接状态 - 无活跃设备"""
        mock_auth._execute_result.scalars.return_value.all.return_value = []

        response = client.get(f"{API_PREFIX}/connection-status")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"] == []


class TestChatAPI:
    """对话 API 测试"""

    def test_chat_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_agent_service
    ):
        """测试对话 - 成功"""
        with patch("app.plugin.module_modbus.control.controller.AgentService") as mock_service_class:
            mock_service_instance = MagicMock()
            mock_service_instance.chat = AsyncMock(return_value={
                "session_id": "test-session",
                "reply": "已读取温度值 25.5°C",
                "actions": [],
                "reasoning": None,
                "requires_confirmation": False,
                "pending_confirm_id": None,
            })
            mock_service_class.return_value = mock_service_instance

            response = client.post(
                f"{API_PREFIX}/chat",
                json={"message": "读取温度"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert "reply" in data["data"]

    def test_chat_with_session_id(
        self,
        client,
        mock_auth_dependency,
        mock_auth
    ):
        """测试对话 - 带会话ID"""
        with patch("app.plugin.module_modbus.control.controller.AgentService") as mock_service_class:
            mock_service_instance = MagicMock()
            mock_service_instance.chat = AsyncMock(return_value={
                "session_id": "existing-session",
                "reply": "继续对话",
                "actions": [],
                "reasoning": None,
                "requires_confirmation": False,
                "pending_confirm_id": None,
            })
            mock_service_class.return_value = mock_service_instance

            response = client.post(
                f"{API_PREFIX}/chat",
                json={"message": "继续", "session_id": "existing-session"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0

    def test_chat_empty_message(
        self,
        client,
        mock_auth_dependency,
        mock_auth
    ):
        """测试对话 - 空消息"""
        response = client.post(
            f"{API_PREFIX}/chat",
            json={"message": ""}
        )

        # 空消息应该通过 Pydantic 验证失败
        assert response.status_code == 422


class TestChatStreamAPI:
    """流式对话 API 测试"""

    def test_chat_stream_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth
    ):
        """测试流式对话 - 成功"""
        async def mock_stream():
            yield {"type": "text", "content": "测试响应"}

        with patch("app.plugin.module_modbus.control.controller.AgentService") as mock_service_class:
            mock_service_instance = MagicMock()
            mock_service_instance.stream_chat = AsyncMock(return_value=mock_stream())
            mock_service_class.return_value = mock_service_instance

            response = client.post(
                f"{API_PREFIX}/chat/stream",
                json={"message": "读取温度"}
            )

            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")


class TestReadPLC:
    """直接读取 PLC 测试"""

    def test_read_plc_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth
    ):
        """测试直接读取 PLC - 成功"""
        with patch("app.plugin.module_modbus.control.controller.PLCService") as mock_service_class:
            mock_service_instance = MagicMock()
            mock_service_instance.read = AsyncMock(return_value={
                "success": True,
                "value": 25.5,
                "raw_value": 255,
                "unit": "C",
                "message": "读取成功",
            })
            mock_service_class.return_value = mock_service_instance

            response = client.post(
                f"{API_PREFIX}/read",
                json={"device_id": 1, "tag_name": "TEMP_001"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["value"] == 25.5

    def test_read_plc_failed(
        self,
        client,
        mock_auth_dependency,
        mock_auth
    ):
        """测试直接读取 PLC - 失败"""
        with patch("app.plugin.module_modbus.control.controller.PLCService") as mock_service_class:
            mock_service_instance = MagicMock()
            mock_service_instance.read = AsyncMock(return_value={
                "success": False,
                "message": "设备离线",
            })
            mock_service_class.return_value = mock_service_instance

            response = client.post(
                f"{API_PREFIX}/read",
                json={"device_id": 1, "tag_name": "TEMP_001"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["code"] != 200


class TestWritePLC:
    """直接写入 PLC 测试"""

    def test_write_plc_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth
    ):
        """测试直接写入 PLC - 成功"""
        with patch("app.plugin.module_modbus.control.controller.PLCService") as mock_service_class:
            mock_service_instance = MagicMock()
            mock_service_instance.write = AsyncMock(return_value={
                "success": True,
                "value": 50.0,
                "unit": "C",
                "message": "写入成功",
            })
            mock_service_class.return_value = mock_service_instance

            response = client.post(
                f"{API_PREFIX}/write",
                json={"device_id": 1, "tag_name": "TEMP_SETPOINT", "value": 50.0}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0

    def test_write_plc_requires_confirmation(
        self,
        client,
        mock_auth_dependency,
        mock_auth
    ):
        """测试直接写入 PLC - 需要确认"""
        with patch("app.plugin.module_modbus.control.controller.PLCService") as mock_service_class:
            mock_service_instance = MagicMock()
            mock_service_instance.write = AsyncMock(return_value={
                "success": False,
                "requires_confirmation": True,
                "pending_confirm_id": 1,
                "message": "此操作需要确认",
            })
            mock_service_class.return_value = mock_service_instance

            response = client.post(
                f"{API_PREFIX}/write",
                json={"device_id": 1, "tag_name": "CRITICAL_VALUE", "value": 100.0}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["requires_confirmation"] is True


class TestQuickCommandsAPI:
    """快捷指令 API 测试"""

    def test_get_quick_commands_success(
        self,
        client,
        mock_auth_dependency,
        mock_auth
    ):
        """测试获取快捷指令 - 成功"""
        with patch("app.plugin.module_modbus.control.controller.QUICK_COMMANDS_CONFIG_PATH") as mock_path:
            mock_path.exists.return_value = True
            mock_path.open = MagicMock()
            mock_path.open.return_value.__enter__ = MagicMock()
            mock_path.open.return_value.__exit__ = MagicMock()
            mock_path.open.return_value.read.return_value = '{"quick_commands": [{"name": "读取温度"}]}'

            with patch("builtins.open", MagicMock(return_value=mock_path.open.return_value)):
                with patch("json.load") as mock_load:
                    mock_load.return_value = {"quick_commands": [{"name": "读取温度"}]}

                    response = client.get(f"{API_PREFIX}/quick-commands")

                    assert response.status_code == 200
                    data = response.json()
                    assert data["code"] == 0

    def test_get_quick_commands_file_not_found(
        self,
        client,
        mock_auth_dependency,
        mock_auth
    ):
        """测试获取快捷指令 - 文件不存在"""
        with patch("app.plugin.module_modbus.control.controller.QUICK_COMMANDS_CONFIG_PATH") as mock_path:
            mock_path.exists.return_value = False

            response = client.get(f"{API_PREFIX}/quick-commands")

            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["quick_commands"] == []


class TestChatHistoryAPI:
    """聊天历史 API 测试"""

    def test_get_chat_history_list(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_chat_history_model
    ):
        """测试获取聊天历史列表"""
        mock_auth.db.execute.side_effect = [
            MagicMock(scalar=lambda: 1),  # count
            MagicMock(scalars=lambda: MagicMock(all=lambda: [mock_chat_history_model])),  # query
        ]

        response = client.get(f"{API_PREFIX}/chat-history")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "items" in data["data"]

    def test_get_chat_history_detail(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_chat_history_model
    ):
        """测试获取聊天历史详情"""
        mock_auth._execute_result.scalar_one_or_none.return_value = mock_chat_history_model

        response = client.get(f"{API_PREFIX}/chat-history/session-123")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["session_id"] == "session-123"

    def test_save_chat_history(
        self,
        client,
        mock_auth_dependency,
        mock_auth
    ):
        """测试保存聊天历史"""
        response = client.post(
            f"{API_PREFIX}/chat-history",
            json={
                "session_id": "new-session",
                "messages": [
                    {"role": "user", "content": "读取温度", "timestamp": "2026-03-25T10:00:00Z"}
                ],
                "device_count": 1,
                "device_names": ["测试PLC"]
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "session_id" in data["data"]

    def test_delete_chat_history(
        self,
        client,
        mock_auth_dependency,
        mock_auth,
        mock_chat_history_model
    ):
        """测试删除聊天历史"""
        mock_auth._execute_result.scalar_one_or_none.return_value = mock_chat_history_model

        response = client.delete(f"{API_PREFIX}/chat-history/session-123")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "删除" in data["msg"]

    def test_clear_all_chat_history(
        self,
        client,
        mock_auth_dependency,
        mock_auth
    ):
        """测试清空所有聊天历史"""
        mock_result = MagicMock()
        mock_result.rowcount = 5
        mock_auth._execute_result = mock_result

        response = client.delete(f"{API_PREFIX}/chat-history")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "清空" in data["msg"]
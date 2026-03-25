import { onUnmounted, ref } from "vue";
import { useModbusStore } from "@/store/modules/modbus.store";
import { useUserStore } from "@/store/modules/user.store";

export interface WebSocketMessage {
  type: "device_status" | "tag_value" | "operation_result" | "pong";
  data: Record<string, unknown>;
  timestamp?: string;
}

export function useModbusWs() {
  const modbusStore = useModbusStore();
  const userStore = useUserStore();

  const ws = ref<WebSocket | null>(null);
  const reconnectAttempts = ref(0);
  const maxReconnectAttempts = 5;
  const reconnectInterval = 3000;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  function connect() {
    if (ws.value?.readyState === WebSocket.OPEN) {
      return;
    }

    modbusStore.setWsConnecting(true);

    // 获取 token
    const token = userStore.getBasicInfo?.token || localStorage.getItem("token");
    if (!token) {
      console.error("[Modbus WS] No token available");
      return;
    }

    // 构建 WebSocket URL - 使用当前页面 host，通过 Vite proxy 转发
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/modbus?token=${token}`;

    try {
      ws.value = new WebSocket(wsUrl);

      ws.value.onopen = () => {
        console.log("[Modbus WS] Connected");
        modbusStore.setWsConnected(true);
        modbusStore.setWsConnecting(false);
        reconnectAttempts.value = 0;
      };

      ws.value.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          handleMessage(message);
        } catch (error) {
          console.error("[Modbus WS] Parse message error:", error);
        }
      };

      ws.value.onerror = (error) => {
        console.error("[Modbus WS] Error:", error);
      };

      ws.value.onclose = () => {
        console.log("[Modbus WS] Disconnected");
        modbusStore.setWsConnected(false);
        scheduleReconnect();
      };
    } catch (error) {
      console.error("[Modbus WS] Connect error:", error);
      modbusStore.setWsConnecting(false);
      scheduleReconnect();
    }
  }

  function disconnect() {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (ws.value) {
      ws.value.close();
      ws.value = null;
    }
    modbusStore.setWsConnected(false);
  }

  function scheduleReconnect() {
    if (reconnectAttempts.value >= maxReconnectAttempts) {
      console.log("[Modbus WS] Max reconnect attempts reached");
      return;
    }

    if (reconnectTimer) return;

    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      reconnectAttempts.value++;
      console.log(
        `[Modbus WS] Reconnecting... (attempt ${reconnectAttempts.value})`
      );
      connect();
    }, reconnectInterval);
  }

  function handleMessage(message: WebSocketMessage) {
    switch (message.type) {
      case "device_status":
        handleDeviceStatus(message.data);
        break;
      case "tag_value":
        handleTagValue(message.data);
        break;
      case "operation_result":
        handleOperationResult(message.data);
        break;
      case "pong":
        // 心跳响应
        break;
    }
  }

  function handleDeviceStatus(data: Record<string, unknown>) {
    const deviceId = data.device_id as number;
    const status = data.status as string;
    const lastSeen = data.last_seen as string | undefined;
    modbusStore.updateDeviceStatus(deviceId, status, lastSeen);
  }

  function handleTagValue(data: Record<string, unknown>) {
    const tagId = data.tag_id as number;
    const value = data.value as number;
    modbusStore.updateTagValue(tagId, value);
  }

  function handleOperationResult(data: Record<string, unknown>) {
    // 可以通过事件或者通知系统处理
    console.log("[Modbus WS] Operation result:", data);
  }

  function sendHeartbeat() {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ type: "ping" }));
    }
  }

  // 心跳定时器
  let heartbeatTimer: ReturnType<typeof setInterval> | null = null;

  function startHeartbeat() {
    if (heartbeatTimer) return;
    heartbeatTimer = setInterval(sendHeartbeat, 30000); // 30秒心跳
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }
  }

  // 手动连接（不自动连接）
  function manualConnect() {
    connect();
    startHeartbeat();
  }

  // 手动断开
  function manualDisconnect() {
    stopHeartbeat();
    disconnect();
  }

  // 组件卸载时清理
  onUnmounted(() => {
    stopHeartbeat();
    disconnect();
  });

  return {
    ws,
    wsConnected: modbusStore.wsConnected,
    wsConnecting: modbusStore.wsConnecting,
    connect: manualConnect,
    disconnect: manualDisconnect,
  };
}
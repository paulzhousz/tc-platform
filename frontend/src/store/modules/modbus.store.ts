import { defineStore } from "pinia";
import { DeviceAPI, ControlAPI, LogAPI } from "@/api/module_modbus";
import type {
  Device,
  TagPoint,
  ActionStep,
  ChatMessage,
  ChatHistoryItem,
} from "@/api/module_modbus";

const MAX_HISTORY_SESSIONS = 50;

export const useModbusStore = defineStore("modbus", {
  state: () => ({
    // 设备相关
    devices: [] as Device[],
    currentDevice: null as Device | null,
    deviceLoading: false,

    // 点位相关
    tagPoints: [] as TagPoint[],
    tagLoading: false,
    deviceTagPointsMap: {} as Record<number, TagPoint[]>,

    // 对话相关
    messages: [] as ChatMessage[],
    sessionId: "",
    chatLoading: false,

    // WebSocket 连接状态
    wsConnected: false,
    wsConnecting: false,

    // 聊天历史
    chatHistory: [] as ChatSession[],
    chatHistoryLoading: false,

    // 快捷指令
    quickCommands: [] as QuickCommand[],

    // 连接状态
    connectionStatus: [] as ConnectionStatusItem[],
  }),

  getters: {
    onlineDevices: (state) => state.devices.filter((d) => d.device_status === "online"),
    offlineDevices: (state) => state.devices.filter((d) => d.device_status !== "online"),
    deviceTree: (state) => {
      const groups: Record<string, Device[]> = {};
      state.devices.forEach((device) => {
        const group = device.group_name || "默认分组";
        if (!groups[group]) {
          groups[group] = [];
        }
        groups[group].push(device);
      });
      return groups;
    },
  },

  actions: {
    // ==================== 设备操作 ====================

    async loadDevices(params?: { group?: string; status?: string }) {
      this.deviceLoading = true;
      try {
        const result = await DeviceAPI.getList(params);
        this.devices = result.data.data?.items || [];
        return result;
      } finally {
        this.deviceLoading = false;
      }
    },

    async loadAllDeviceTagPoints() {
      const onlineDeviceIds = this.onlineDevices.map((d) => d.id);
      const promises = onlineDeviceIds.map(async (deviceId) => {
        try {
          const result = await DeviceAPI.getTags(deviceId);
          this.deviceTagPointsMap[deviceId] = result.data.data?.items || [];
          return { deviceId, success: true };
        } catch {
          this.deviceTagPointsMap[deviceId] = [];
          return { deviceId, success: false };
        }
      });
      await Promise.all(promises);
    },

    setCurrentDevice(device: Device | null) {
      this.currentDevice = device;
      if (device) {
        this.loadTagPoints(device.id);
      } else {
        this.tagPoints = [];
      }
    },

    // ==================== 点位操作 ====================

    async loadTagPoints(deviceId: number) {
      this.tagLoading = true;
      try {
        const result = await DeviceAPI.getTags(deviceId);
        this.tagPoints = result.data.data?.items || [];
        return result;
      } finally {
        this.tagLoading = false;
      }
    },

    // ==================== 对话操作 ====================

    async sendMessage(content: string) {
      if (!content.trim()) return;

      // 添加用户消息
      this.messages.push({
        role: "user",
        content,
        timestamp: new Date().toISOString(),
      });

      this.chatLoading = true;
      try {
        const result = await ControlAPI.chat({
          message: content,
          session_id: this.sessionId || undefined,
        });

        // 更新 session_id
        if (result.data.data?.session_id) {
          this.sessionId = result.data.data.session_id;
        }

        // 添加助手消息
        this.messages.push({
          role: "assistant",
          content: result.data.data?.reply || "",
          actions: result.data.data?.actions,
          timestamp: new Date().toISOString(),
        });

        return result;
      } finally {
        this.chatLoading = false;
      }
    },

    // 流式对话操作
    abortStream: null as (() => void) | null,

    sendMessageStream(content: string): Promise<void> {
      if (!content.trim()) return Promise.resolve();

      // 添加用户消息
      this.messages.push({
        role: "user",
        content,
        timestamp: new Date().toISOString(),
      });

      // 添加占位的助手消息
      const assistantIndex = this.messages.length;
      this.messages.push({
        role: "assistant",
        content: "",
        actions: [],
        timestamp: new Date().toISOString(),
      });

      this.chatLoading = true;

      return new Promise((resolve, reject) => {
        const actions: ActionStep[] = [];

        this.abortStream = ControlAPI.chatStream(
          {
            message: content,
            session_id: this.sessionId || undefined,
          },
          (event) => {
            // 处理流式事件
            if (event.type === "session" && event.session_id) {
              this.sessionId = event.session_id;
            } else if (event.type === "token" && event.content) {
              // 更新消息内容
              this.messages[assistantIndex].content += event.content;
            } else if (event.type === "action_start" && event.action) {
              // 添加新的 action（完整复制后端返回的所有字段）
              const action = event.action;
              actions.push({
                tool: action.tool,
                args: action.args || {},
                status: action.status || "running",
                started_at: action.started_at,
                result: undefined,
              });
              this.messages[assistantIndex].actions = [...actions];
            } else if (event.type === "action_end" && event.action) {
              // 更新 action 结果（更新所有字段）
              const action = event.action;
              const idx = actions.findIndex((a) => a.tool === action.tool);
              if (idx >= 0) {
                // 更新所有可能的字段
                actions[idx].result = action.result;
                actions[idx].status = action.status;
                actions[idx].data = action.data;
                actions[idx].error = action.error;
                actions[idx].duration_ms = action.duration_ms;
                actions[idx].finished_at = action.finished_at;
                this.messages[assistantIndex].actions = [...actions];
              }
            } else if (event.type === "done") {
              // 流式完成
              this.messages[assistantIndex].content =
                event.reply || this.messages[assistantIndex].content;
              const finalActions = event.actions || (actions.length > 0 ? actions : undefined);
              this.messages[assistantIndex].actions = finalActions;
              this.chatLoading = false;
              this.abortStream = null;
              resolve();
            } else if (event.type === "error") {
              // 错误处理
              this.messages[assistantIndex].content = `错误: ${event.error || "未知错误"}`;
              this.chatLoading = false;
              this.abortStream = null;
              reject(new Error(event.error));
            }
          },
          (error) => {
            this.messages[assistantIndex].content = `请求失败: ${error.message}`;
            this.chatLoading = false;
            this.abortStream = null;
            reject(error);
          }
        );
      });
    },

    clearMessages() {
      this.messages = [];
      this.sessionId = "";
      if (this.abortStream) {
        try {
          this.abortStream();
        } catch {
          // 忽略 abort 可能的错误（如已完成的请求）
        }
        this.abortStream = null;
      }
    },

    abortGeneration() {
      if (this.abortStream) {
        this.abortStream();
        this.abortStream = null;
      }
      this.chatLoading = false;
      // 移除最后一条正在生成的助手消息（如果存在且为空）
      if (this.messages.length > 0) {
        const lastMsg = this.messages[this.messages.length - 1];
        if (lastMsg.role === "assistant" && !lastMsg.content) {
          this.messages.pop();
        }
      }
    },

    // ==================== 聊天历史操作 ====================

    async loadChatHistory() {
      this.chatHistoryLoading = true;
      try {
        const result = await ControlAPI.getChatHistoryList({
          page_no: 1,
          page_size: MAX_HISTORY_SESSIONS,
        });
        this.chatHistory = (result.data.data?.items || []).map((item) => ({
          id: item.id,
          sessionId: item.session_id,
          title: item.title,
          startTime: item.start_time,
          endTime: item.end_time,
          messages: [],
          deviceCount: item.device_count,
          deviceNames: item.device_names,
        }));
      } catch (error) {
        console.error("Failed to load chat history:", error);
      } finally {
        this.chatHistoryLoading = false;
      }
    },

    async loadChatFromHistory(sessionIdToLoad: string) {
      try {
        const result = await ControlAPI.getChatHistoryDetail(sessionIdToLoad);
        if (result.data.data) {
          this.messages = result.data.data.messages.map((msg) => ({
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp,
            actions: msg.actions,
          }));
          this.sessionId = result.data.data.session_id;
        }
      } catch (error) {
        console.error("Failed to load chat from history:", error);
      }
    },

    async deleteChatHistory(sessionIdToDelete: string) {
      try {
        await ControlAPI.deleteChatHistory(sessionIdToDelete);
        // 从本地列表中移除
        const index = this.chatHistory.findIndex((s) => s.sessionId === sessionIdToDelete);
        if (index > -1) {
          this.chatHistory.splice(index, 1);
        }
      } catch (error) {
        console.error("Failed to delete chat history:", error);
      }
    },

    async saveChatHistory(deviceCount: number = 0, deviceNames: string[] = []) {
      // 消息为空时不保存
      if (this.messages.length === 0 || !this.sessionId) {
        return { success: false, reason: "no_messages" };
      }

      try {
        await ControlAPI.saveChatHistory({
          session_id: this.sessionId,
          messages: this.messages.map((msg) => ({
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp,
            actions: msg.actions,
          })),
          device_count: deviceCount,
          device_names: deviceNames,
        });

        // 刷新历史列表
        await this.loadChatHistory();

        return { success: true };
      } catch (error) {
        console.error("Failed to save chat history:", error);
        return { success: false, reason: "error" };
      }
    },

    // ==================== 连接操作 ====================

    async loadConnectionStatus() {
      try {
        const result = await ControlAPI.getConnectionStatus();
        this.connectionStatus = result.data.data || [];
      } catch (error) {
        console.error("Failed to load connection status:", error);
      }
    },

    async connectDevices(deviceIds?: number[]) {
      return await ControlAPI.connect(deviceIds);
    },

    async disconnectDevices(deviceIds?: number[]) {
      return await ControlAPI.disconnect(deviceIds);
    },

    // ==================== 快捷指令 ====================

    async loadQuickCommands() {
      try {
        const result = await ControlAPI.getQuickCommands();
        this.quickCommands = result.data.data?.quick_commands || [];
      } catch (error) {
        console.error("Failed to load quick commands:", error);
      }
    },

    // ==================== WebSocket 状态 ====================

    setWsConnected(connected: boolean) {
      this.wsConnected = connected;
      this.wsConnecting = false;
    },

    setWsConnecting(connecting: boolean) {
      this.wsConnecting = connecting;
    },

    // 更新设备状态（WebSocket 回调）
    updateDeviceStatus(deviceId: number, status: string, lastSeen?: string) {
      const device = this.devices.find((d) => d.id === deviceId);
      if (device) {
        device.device_status = status as Device["device_status"];
        if (lastSeen) {
          device.last_seen = lastSeen;
        }
      }
    },

    // 更新点位值（WebSocket 回调）
    updateTagValue(tagId: number, value: number) {
      const tag = this.tagPoints.find((t) => t.id === tagId);
      if (tag) {
        tag.current_value = value;
        tag.last_updated = new Date().toISOString();
      }
    },
  },
});

// ==================== Types ====================

export interface ChatSession {
  id: number;
  sessionId: string;
  title?: string;
  startTime: string;
  endTime?: string;
  messages: ChatMessage[];
  deviceCount: number;
  deviceNames: string[];
}

export interface QuickCommand {
  id: string;
  label: { zh: string; en: string };
  text: { zh: string; en: string };
}

export interface ConnectionStatusItem {
  device_id: number;
  device_name: string;
  status: string;
  connected: boolean;
  available_connections: number;
  max_connections: number;
}

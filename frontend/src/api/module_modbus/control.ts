import request from "@/utils/request";
import { Auth } from "@/utils/auth";

const API_PATH = "/modbus/control";

// ==================== Types ====================

/** ActionStep 执行状态 */
export type ActionStatus = "running" | "success" | "failed" | "pending" | "cancelled";

/** ActionStep 结构化数据 */
export interface ActionStepData {
  device_id?: number;
  device_name?: string;
  tag_id?: number;
  tag_name?: string;
  unit?: string;
  value?: number;
  raw_value?: number;
  min_value?: number;
  max_value?: number;
  previous_value?: number;
  delta?: number;
  new_value?: number;
  request_value?: number;
  actual_value?: number;
  execution_time_ms?: number;
  [key: string]: unknown;
}

/** ActionStep 执行步骤 */
export interface ActionStep {
  tool: string;
  args: Record<string, unknown>;
  status?: ActionStatus;
  started_at?: string;
  finished_at?: string;
  duration_ms?: number;
  result?: string;
  error?: string;
  data?: ActionStepData;
  command_log_id?: number;
}

/** 聊天消息 */
export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  actions?: ActionStep[];
}

/** 聊天历史项 */
export interface ChatHistoryItem {
  id: number;
  session_id: string;
  title?: string;
  device_count: number;
  device_names: string[];
  start_time: string;
  end_time?: string;
  created_time: string;
}

/** 聊天历史详情 */
export interface ChatHistoryDetail extends ChatHistoryItem {
  messages: ChatMessage[];
}

/** 快捷指令项 */
export interface QuickCommand {
  id: string;
  label: { zh: string; en: string };
  text: { zh: string; en: string };
}

// ==================== Control API ====================

const ControlAPI = {
  /** 连接设备 */
  connect(deviceIds?: number[]) {
    return request<
      ApiResponse<{
        message: string;
        results: Array<{
          device_id: number;
          device_name: string;
          success: boolean;
          error?: string;
        }>;
      }>
    >({
      url: `${API_PATH}/connect`,
      method: "post",
      data: deviceIds,
    });
  },

  /** 断开设备连接 */
  disconnect(deviceIds?: number[]) {
    return request<ApiResponse<{ message: string }>>({
      url: `${API_PATH}/disconnect`,
      method: "post",
      data: deviceIds,
    });
  },

  /** 获取设备连接状态 */
  getConnectionStatus() {
    return request<
      ApiResponse<
        Array<{
          device_id: number;
          device_name: string;
          status: string;
          connected: boolean;
          available_connections: number;
          max_connections: number;
        }>
      >
    >({
      url: `${API_PATH}/connection-status`,
      method: "get",
    });
  },

  /** 发送对话消息 */
  chat(data: ChatRequest) {
    return request<ApiResponse<ChatResponse>>({
      url: `${API_PATH}/chat`,
      method: "post",
      data,
      timeout: 120000, // LLM 调用可能需要较长时间，设置 2 分钟超时
    });
  },

  /** 流式对话消息 (SSE) */
  chatStream(
    data: ChatRequest,
    onEvent: (event: StreamEvent) => void,
    onError?: (error: Error) => void
  ) {
    // 使用 Auth 工具类获取 token（支持"记住我"功能）
    const token = Auth.getAccessToken();
    // 使用 Vite proxy 前缀 (VITE_APP_BASE_API=/api/v1)
    const baseUrl = import.meta.env.VITE_APP_BASE_API;
    const url = `${baseUrl}/modbus/control/chat/stream`;
    const controller = new AbortController();

    fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: token ? `Bearer ${token}` : "",
      },
      body: JSON.stringify(data),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const reader = response.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const event = JSON.parse(line.slice(6));
                onEvent(event);
              } catch {
                // 忽略解析错误
              }
            }
          }
        }
      })
      .catch((error) => {
        if (error.name !== "AbortError" && onError) {
          onError(error);
        }
      });

    return () => controller.abort();
  },

  /** 读取 PLC 点位 */
  read(data: ReadRequest) {
    return request<
      ApiResponse<{
        device_id: number;
        tag_name: string;
        value: number;
        raw_value: number;
        unit?: string;
      }>
    >({
      url: `${API_PATH}/read`,
      method: "post",
      data,
    });
  },

  /** 写入 PLC 点位 */
  write(data: WriteRequest) {
    return request<
      ApiResponse<{
        success: boolean;
        requires_confirmation?: boolean;
        pending_confirm_id?: number;
        value?: number;
        unit?: string;
        message?: string;
      }>
    >({
      url: `${API_PATH}/write`,
      method: "post",
      data,
    });
  },

  /** 获取快捷指令配置 */
  getQuickCommands() {
    return request<ApiResponse<{ quick_commands: QuickCommand[] }>>({
      url: `${API_PATH}/quick-commands`,
      method: "get",
    });
  },

  /** 获取 Modbus 配置 */
  getConfig() {
    return request<ApiResponse<ModbusConfig>>({
      url: `${API_PATH}/config`,
      method: "get",
    });
  },

  // ==================== Chat History API ====================

  /** 获取聊天历史列表 */
  getChatHistoryList(params?: { page_no?: number; page_size?: number }) {
    return request<ApiResponse<{ items: ChatHistoryItem[]; total: number }>>({
      url: `${API_PATH}/chat-history`,
      method: "get",
      params,
    });
  },

  /** 获取聊天历史详情 */
  getChatHistoryDetail(sessionId: string) {
    return request<ApiResponse<ChatHistoryDetail>>({
      url: `${API_PATH}/chat-history/${sessionId}`,
      method: "get",
    });
  },

  /** 删除聊天历史 */
  deleteChatHistory(sessionId: string) {
    return request<ApiResponse<{ message: string }>>({
      url: `${API_PATH}/chat-history/${sessionId}`,
      method: "delete",
    });
  },

  /** 保存聊天历史 */
  saveChatHistory(data: ChatHistorySaveRequest) {
    return request<ApiResponse<{ id: number; session_id: string }>>({
      url: `${API_PATH}/chat-history`,
      method: "post",
      data,
    });
  },
};

export default ControlAPI;

// ==================== Parameter Types ====================

export interface ChatRequest {
  message: string;
  session_id?: string;
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  actions?: ActionStep[];
  reasoning?: string;
  requires_confirmation: boolean;
  pending_confirm_id?: number;
}

export interface StreamEvent {
  type: "session" | "token" | "action_start" | "action_end" | "done" | "error";
  session_id?: string;
  content?: string;
  action?: ActionStep;
  reply?: string;
  actions?: ActionStep[];
  error?: string;
}

export interface ReadRequest {
  device_id: number;
  tag_name: string;
}

export interface WriteRequest {
  device_id: number;
  tag_name: string;
  value: number;
}

/** 保存聊天历史请求 */
export interface ChatHistorySaveRequest {
  session_id: string;
  messages: ChatMessage[];
  device_count?: number;
  device_names?: string[];
}

/** Modbus 运行时配置 */
export interface ModbusConfig {
  // LLM 配置
  modbus_llm_model_name: string;
  modbus_llm_temperature: number;
  modbus_llm_session_ttl_minutes: number;
  modbus_llm_max_history_turns: number;
  // 重试配置
  modbus_retry_enabled: boolean;
  modbus_retry_times: number;
  modbus_retry_interval: number;
  // 轮询配置
  modbus_poll_enabled: boolean;
  modbus_poll_interval: number;
  // 待确认配置
  modbus_pending_expire_minutes: number;
  // FunASR 配置
  modbus_funasr_mode: string;
  modbus_silence_threshold: number;
  modbus_silence_duration: number;
  // 聊天历史配置
  modbus_chat_save_min_messages: number;
}
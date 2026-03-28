import request from "@/utils/request";

const API_PATH = "/modbus/log";

// ==================== Types ====================

/** 操作日志 */
export interface CommandLog {
  id: number;
  user_id: number;
  session_id?: string;
  device_id?: number;
  tag_id?: number;
  action: "READ" | "WRITE";
  request_value?: number;
  actual_value?: number;
  log_status: "pending" | "success" | "failed" | "cancelled";
  error_message?: string;
  confirmation_required: boolean;
  confirmed_by?: number;
  confirmed_at?: string;
  ai_reasoning?: string;
  user_input?: string;
  retry_count: number;
  execution_time?: number;
  created_time: string;
  executed_at?: string;
}

// ==================== Log API ====================

const LogAPI = {
  /** 获取操作日志列表 */
  getList(params?: LogListParams) {
    return request<ApiResponse<LogListResult>>({
      url: `${API_PATH}/list`,
      method: "get",
      params,
    });
  },

  /** 获取操作日志详情 */
  getDetail(logId: number) {
    return request<ApiResponse<CommandLog>>({
      url: `${API_PATH}/detail/${logId}`,
      method: "get",
    });
  },
};

export default LogAPI;

// ==================== Parameter Types ====================

export interface LogListParams {
  device_id?: number;
  user_id?: number;
  action?: string;
  status?: string;
  start_time?: string;
  end_time?: string;
  page_no?: number;
  page_size?: number;
}

export interface LogListResult {
  items: CommandLog[];
  total: number;
}
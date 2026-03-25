import request from "@/utils/request";

const API_PATH = "/modbus";

// ==================== Types ====================

/** 设备信息 */
export interface Device {
  id: number;
  name: string;
  code: string;
  description?: string;
  group_name?: string;
  connection_type: "TCP" | "RTU_OVER_TCP";
  host: string;
  port: number;
  slave_id: number;
  baud_rate?: number;
  parity?: string;
  status: "online" | "offline" | "error";
  last_seen?: string;
  created_at: string;
  updated_at?: string;
}

/** 点位信息 */
export interface TagPoint {
  id: number;
  device_id: number;
  name: string;
  code: string;
  description?: string;
  address: number;
  register_type: "holding" | "input" | "coil" | "discrete";
  data_type: "INT16" | "UINT16" | "INT32" | "UINT32" | "FLOAT" | "BOOL";
  byte_order?: string;
  access_type: "READ" | "WRITE" | "READ_WRITE";
  min_value: number;
  max_value: number;
  unit?: string;
  scale_factor: number;
  offset: number;
  aliases?: string[];
  requires_confirmation: boolean;
  confirmation_threshold?: number;
  sort_order?: number;
  is_active: boolean;
  current_value?: number;
  last_updated?: string;
  created_at: string;
}

// ==================== Device API ====================

const DeviceAPI = {
  /** 获取设备列表 */
  getList(params?: DeviceListParams) {
    return request<ApiResponse<DeviceListResult>>({
      url: `${API_PATH}/device/list`,
      method: "get",
      params,
    });
  },

  /** 获取设备详情 */
  getDetail(deviceId: number) {
    return request<ApiResponse<Device>>({
      url: `${API_PATH}/device/${deviceId}`,
      method: "get",
    });
  },

  /** 创建设备 */
  create(data: DeviceCreateData) {
    return request<ApiResponse<Device>>({
      url: `${API_PATH}/device`,
      method: "post",
      data,
    });
  },

  /** 更新设备 */
  update(deviceId: number, data: DeviceUpdateData) {
    return request<ApiResponse<Device>>({
      url: `${API_PATH}/device/${deviceId}`,
      method: "put",
      data,
    });
  },

  /** 删除设备 */
  delete(deviceId: number) {
    return request<ApiResponse<{ message: string }>>({
      url: `${API_PATH}/device/${deviceId}`,
      method: "delete",
    });
  },

  /** 获取设备点位列表 */
  getTags(deviceId: number, params?: TagPointListParams) {
    return request<ApiResponse<TagPointListResult>>({
      url: `${API_PATH}/device/${deviceId}/tags`,
      method: "get",
      params,
    });
  },

  /** 创建点位 */
  createTag(deviceId: number, data: TagPointCreateData) {
    return request<ApiResponse<TagPoint>>({
      url: `${API_PATH}/device/${deviceId}/tags`,
      method: "post",
      data,
    });
  },

  /** 更新点位 */
  updateTag(tagId: number, data: TagPointUpdateData) {
    return request<ApiResponse<TagPoint>>({
      url: `${API_PATH}/device/tags/${tagId}`,
      method: "put",
      data,
    });
  },

  /** 删除点位 */
  deleteTag(tagId: number) {
    return request<ApiResponse<{ message: string }>>({
      url: `${API_PATH}/device/tags/${tagId}`,
      method: "delete",
    });
  },
};

export default DeviceAPI;

// ==================== Parameter Types ====================

export interface DeviceListParams {
  group?: string;
  status?: string;
}

export interface DeviceListResult {
  items: Device[];
  total: number;
}

export interface DeviceCreateData {
  name: string;
  code: string;
  description?: string;
  group_name?: string;
  connection_type: "TCP" | "RTU_OVER_TCP";
  host: string;
  port: number;
  slave_id: number;
  baud_rate?: number;
  parity?: string;
}

export interface DeviceUpdateData {
  name?: string;
  description?: string;
  group_name?: string;
  connection_type?: "TCP" | "RTU_OVER_TCP";
  host?: string;
  port?: number;
  slave_id?: number;
  baud_rate?: number;
  parity?: string;
}

export interface TagPointListParams {
  name?: string;
  register_type?: string;
  page?: number;
  page_size?: number;
  is_active?: boolean;
}

export interface TagPointListResult {
  items: TagPoint[];
  total: number;
}

export interface TagPointCreateData {
  name: string;
  code: string;
  description?: string;
  address: number;
  register_type: "holding" | "input" | "coil" | "discrete";
  data_type: "INT16" | "UINT16" | "INT32" | "UINT32" | "FLOAT" | "BOOL";
  byte_order?: string;
  access_type: "READ" | "WRITE" | "READ_WRITE";
  min_value: number;
  max_value: number;
  unit?: string;
  scale_factor?: number;
  offset?: number;
  aliases?: string[];
  requires_confirmation?: boolean;
  confirmation_threshold?: number;
  sort_order?: number;
  is_active?: boolean;
}

export interface TagPointUpdateData {
  name?: string;
  description?: string;
  address?: number;
  register_type?: "holding" | "input" | "coil" | "discrete";
  data_type?: "INT16" | "UINT16" | "INT32" | "UINT32" | "FLOAT" | "BOOL";
  access_type?: "READ" | "WRITE" | "READ_WRITE";
  min_value?: number;
  max_value?: number;
  unit?: string;
  scale_factor?: number;
  offset?: number;
  aliases?: string[];
  requires_confirmation?: boolean;
  confirmation_threshold?: number;
  sort_order?: number;
  is_active?: boolean;
}
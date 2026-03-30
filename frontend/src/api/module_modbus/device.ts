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
  device_status: "online" | "offline" | "error";
  last_seen?: string;
  created_time: string;
  updated_time?: string;
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
  created_time: string;
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
      url: `${API_PATH}/device/detail/${deviceId}`,
      method: "get",
    });
  },

  /** 创建设备 */
  create(data: DeviceCreateData) {
    return request<ApiResponse<Device>>({
      url: `${API_PATH}/device/create`,
      method: "post",
      data,
    });
  },

  /** 更新设备 */
  update(deviceId: number, data: DeviceUpdateData) {
    return request<ApiResponse<Device>>({
      url: `${API_PATH}/device/update/${deviceId}`,
      method: "put",
      data,
    });
  },

  /** 删除设备 - 通过 body 传递 id 数组，支持批量删除 */
  delete(ids: number[]) {
    return request<ApiResponse<{ message: string }>>({
      url: `${API_PATH}/device/delete`,
      method: "delete",
      data: ids,
    });
  },

  /** 获取设备点位列表 */
  getTags(deviceId: number, params?: TagPointListParams) {
    return request<ApiResponse<TagPointListResult>>({
      url: `${API_PATH}/device/${deviceId}/tag/list`,
      method: "get",
      params,
    });
  },

  /** 创建点位 */
  createTag(deviceId: number, data: TagPointCreateData) {
    return request<ApiResponse<TagPoint>>({
      url: `${API_PATH}/device/${deviceId}/tag/create`,
      method: "post",
      data,
    });
  },

  /** 更新点位 */
  updateTag(tagId: number, data: TagPointUpdateData) {
    return request<ApiResponse<TagPoint>>({
      url: `${API_PATH}/device/tag/update/${tagId}`,
      method: "put",
      data,
    });
  },

  /** 删除点位 - 通过 body 传递 id 数组，支持批量删除 */
  deleteTag(ids: number[]) {
    return request<ApiResponse<{ message: string }>>({
      url: `${API_PATH}/device/tag/delete`,
      method: "delete",
      data: ids,
    });
  },

  /** 测试设备连接 */
  testConnection(deviceId: number) {
    return request<ApiResponse<{ connected: boolean; message: string }>>({
      url: `${API_PATH}/device/${deviceId}/test`,
      method: "post",
    });
  },
};

export default DeviceAPI;

// ==================== Parameter Types ====================

/** 设备列表查询参数 */
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
  page_no?: number;
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

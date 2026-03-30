<!-- Modbus 设备管理 -->
<template>
  <div class="app-container">
    <!-- 内容区域 -->
    <el-card class="data-table">
      <template #header>
        <div class="card-header">
          <span>设备列表</span>
        </div>
        <!-- 搜索区域 -->
        <div class="search-container">
          <el-form
            ref="queryFormRef"
            :model="queryFormData"
            :inline="true"
            label-suffix=":"
            @submit.prevent="handleQuery"
          >
            <el-form-item prop="group_name" label="设备分组">
              <el-select
                v-model="queryFormData.group_name"
                placeholder="全部分组"
                style="width: 150px"
                clearable
              >
                <el-option
                  v-for="group in deviceGroups"
                  :key="group"
                  :value="group"
                  :label="group"
                />
              </el-select>
            </el-form-item>
            <el-form-item prop="status" label="状态">
              <el-select
                v-model="queryFormData.status"
                placeholder="全部状态"
                style="width: 120px"
                clearable
              >
                <el-option value="online" label="在线" />
                <el-option value="offline" label="离线" />
                <el-option value="error" label="异常" />
              </el-select>
            </el-form-item>
            <el-form-item class="search-buttons">
              <el-button type="primary" icon="search" native-type="submit">查询</el-button>
              <el-button icon="refresh" @click="handleResetQuery">重置</el-button>
            </el-form-item>
          </el-form>
          <el-button type="success" icon="plus" @click="handleOpenDeviceDialog()">
            新增设备
          </el-button>
        </div>
      </template>

      <!-- 表格区域 -->
      <div class="data-table__content">
        <el-table
          ref="dataTableRef"
          v-loading="loading"
          row-key="id"
          :data="devices"
          border
          stripe
          @expand-change="handleExpand"
        >
          <template #empty>
            <el-empty :image-size="80" description="暂无数据" />
          </template>
          <el-table-column type="expand">
            <template #default="{ row }">
              <div style="padding: 0 48px">
                <el-table
                  :data="deviceTagsMap[row.id] || []"
                  :loading="expandedRowLoading[row.id]"
                  size="small"
                  border
                >
                  <el-table-column prop="name" label="点位名称" min-width="120" />
                  <el-table-column prop="code" label="点位编码" min-width="100" />
                  <el-table-column prop="address" label="寄存器地址" width="100" />
                  <el-table-column prop="register_type" label="寄存器类型" width="100">
                    <template #default="{ row: tag }">
                      <el-tag size="small">{{ registerTypeMap[tag.register_type] }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="unit" label="单位" width="80" />
                  <el-table-column prop="access_type" label="访问类型" width="100">
                    <template #default="{ row: tag }">
                      <el-tag
                        size="small"
                        :type="tag.access_type === 'READ' ? 'warning' : 'success'"
                      >
                        {{ tag.access_type }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="requires_confirmation" label="需要确认" width="90">
                    <template #default="{ row: tag }">
                      <el-tag v-if="tag.requires_confirmation" size="small" type="danger">
                        是
                      </el-tag>
                      <span v-else>-</span>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="name" label="设备名称" min-width="120" />
          <el-table-column prop="code" label="设备编码" min-width="100" />
          <el-table-column prop="group_name" label="分组" width="100" />
          <el-table-column prop="connection_type" label="连接类型" width="120">
            <template #default="{ row }">
              <el-tag type="primary">{{ row.connection_type }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="host" label="IP地址" width="130" />
          <el-table-column prop="port" label="端口" width="80" />
          <el-table-column prop="slave_id" label="从站ID" width="80" />
          <el-table-column prop="device_status" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.device_status)">
                {{ getStatusText(row.device_status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column fixed="right" label="操作" align="center" min-width="180">
            <template #default="{ row }">
              <el-button type="primary" size="small" link @click="handleOpenTagDrawer(row)">
                点位管理
              </el-button>
              <el-button type="warning" size="small" link @click="handleOpenDeviceDialog(row)">
                编辑
              </el-button>
              <el-popconfirm title="确认删除该设备?" @confirm="handleDeleteDevice(row.id)">
                <template #reference>
                  <el-button type="danger" size="small" link>删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <!-- 设备新增/编辑弹窗 -->
    <el-dialog
      v-model="deviceDialogVisible"
      :title="deviceDialogTitle"
      width="600px"
      @close="handleCloseDeviceDialog"
    >
      <el-form
        ref="deviceFormRef"
        :model="deviceFormData"
        :rules="deviceRules"
        label-suffix=":"
        label-width="100px"
      >
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="设备名称" prop="name">
              <el-input v-model="deviceFormData.name" placeholder="请输入设备名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="设备编码" prop="code">
              <el-input
                v-model="deviceFormData.code"
                placeholder="请输入设备编码"
                :disabled="isEditDevice"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="分组名称" prop="group_name">
              <el-input v-model="deviceFormData.group_name" placeholder="请输入分组名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="连接类型" prop="connection_type">
              <el-select v-model="deviceFormData.connection_type" style="width: 100%">
                <el-option value="TCP" label="TCP" />
                <el-option value="RTU_OVER_TCP" label="RTU over TCP" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="IP地址" prop="host">
              <el-input v-model="deviceFormData.host" placeholder="请输入IP地址" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="端口" prop="port">
              <el-input-number
                v-model="deviceFormData.port"
                :min="1"
                :max="65535"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="从站ID" prop="slave_id">
              <el-input-number
                v-model="deviceFormData.slave_id"
                :min="1"
                :max="255"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="描述" prop="description">
              <el-input v-model="deviceFormData.description" placeholder="请输入描述" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="deviceDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="deviceSubmitLoading" @click="handleDeviceSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 点位管理抽屉 -->
    <el-drawer
      v-model="tagDrawerVisible"
      :title="`${currentDevice?.name || ''} - 点位管理`"
      size="900px"
    >
      <!-- 搜索栏 -->
      <div class="drawer-search-bar">
        <el-form :inline="true" :model="tagQueryFormData">
          <el-form-item label="点位名称">
            <el-input
              v-model="tagQueryFormData.name"
              placeholder="请输入点位名称"
              clearable
              style="width: 150px"
              @keyup.enter="handleTagQuery"
            />
          </el-form-item>
          <el-form-item label="寄存器类型">
            <el-select
              v-model="tagQueryFormData.register_type"
              placeholder="全部类型"
              clearable
              style="width: 120px"
            >
              <el-option value="holding" label="保持寄存器" />
              <el-option value="input" label="输入寄存器" />
              <el-option value="coil" label="线圈" />
              <el-option value="discrete" label="离散输入" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" icon="search" @click="handleTagQuery">查询</el-button>
            <el-button icon="refresh" @click="handleTagResetQuery">重置</el-button>
          </el-form-item>
        </el-form>
        <el-button type="success" size="small" icon="plus" @click="handleOpenTagDialog()">
          新增点位
        </el-button>
      </div>

      <!-- 点位表格 -->
      <el-table v-loading="tagLoading" :data="tagTableData" border stripe size="small">
        <template #empty>
          <el-empty :image-size="60" description="暂无点位数据" />
        </template>
        <el-table-column prop="name" label="点位名称" min-width="120" />
        <el-table-column prop="code" label="点位编码" min-width="100" />
        <el-table-column prop="address" label="寄存器地址" width="100" />
        <el-table-column prop="register_type" label="寄存器类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ registerTypeMap[row.register_type] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="80" />
        <el-table-column prop="access_type" label="访问类型" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.access_type === 'READ' ? 'warning' : 'success'">
              {{ row.access_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="requires_confirmation" label="需要确认" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.requires_confirmation" size="small" type="danger">是</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column fixed="right" label="操作" align="center" width="120">
          <template #default="{ row }">
            <el-button type="warning" size="small" link @click="handleOpenTagDialog(row)">
              编辑
            </el-button>
            <el-popconfirm title="确认删除该点位?" @confirm="handleDeleteTag(row.id)">
              <template #reference>
                <el-button type="danger" size="small" link>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="tagPagination.page_no"
          v-model:page-size="tagPagination.pageSize"
          :total="tagPagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="handleTagSizeChange"
          @current-change="handleTagCurrentChange"
        />
      </div>
    </el-drawer>

    <!-- 点位新增/编辑弹窗 -->
    <el-dialog
      v-model="tagDialogVisible"
      :title="tagDialogTitle"
      width="600px"
      @close="handleCloseTagDialog"
    >
      <el-form
        ref="tagFormRef"
        :model="tagFormData"
        :rules="tagRules"
        label-suffix=":"
        label-width="100px"
      >
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="点位名称" prop="name">
              <el-input v-model="tagFormData.name" placeholder="请输入点位名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="点位编码" prop="code">
              <el-input
                v-model="tagFormData.code"
                placeholder="请输入点位编码"
                :disabled="isEditTag"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="寄存器地址" prop="address">
              <el-input-number v-model="tagFormData.address" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="寄存器类型" prop="register_type">
              <el-select v-model="tagFormData.register_type" style="width: 100%">
                <el-option value="holding" label="保持寄存器" />
                <el-option value="input" label="输入寄存器" />
                <el-option value="coil" label="线圈" />
                <el-option value="discrete" label="离散输入" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="数据类型" prop="data_type">
              <el-select v-model="tagFormData.data_type" style="width: 100%">
                <el-option value="INT16" label="INT16" />
                <el-option value="UINT16" label="UINT16" />
                <el-option value="INT32" label="INT32" />
                <el-option value="FLOAT" label="FLOAT" />
                <el-option value="BOOL" label="BOOL" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="单位" prop="unit">
              <el-input v-model="tagFormData.unit" placeholder="如: ℃" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="最小值" prop="min_value">
              <el-input-number v-model="tagFormData.min_value" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最大值" prop="max_value">
              <el-input-number v-model="tagFormData.max_value" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="缩放因子" prop="scale_factor">
              <el-input-number
                v-model="tagFormData.scale_factor"
                :step="0.1"
                :precision="2"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="偏移量" prop="offset">
              <el-input-number v-model="tagFormData.offset" :precision="2" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="访问类型" prop="access_type">
              <el-select v-model="tagFormData.access_type" style="width: 100%">
                <el-option value="READ" label="只读" />
                <el-option value="WRITE" label="只写" />
                <el-option value="READ_WRITE" label="读写" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="需要确认" prop="requires_confirmation">
              <el-switch v-model="tagFormData.requires_confirmation" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="tagDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="tagSubmitLoading" @click="handleTagSubmit">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: "ModbusDevice",
  inheritAttrs: false,
});

import DeviceAPI, { type Device, type TagPoint } from "@/api/module_modbus/device";

// 查询表单
const queryFormRef = ref();
const queryFormData = reactive({
  group_name: undefined as string | undefined,
  status: undefined as string | undefined,
});

// 设备列表
const devices = ref<Device[]>([]);
const loading = ref(false);

// 设备分组列表
const deviceGroups = computed(() => {
  const groups = new Set<string>();
  devices.value.forEach((d) => {
    if (d.group_name) groups.add(d.group_name);
  });
  return Array.from(groups);
});

// 寄存器类型映射
const registerTypeMap: Record<string, string> = {
  holding: "保持寄存器",
  input: "输入寄存器",
  coil: "线圈",
  discrete: "离散输入",
};

// 状态处理
function getStatusType(status: string) {
  return status === "online" ? "success" : status === "error" ? "danger" : "info";
}

function getStatusText(status: string) {
  return status === "online" ? "在线" : status === "error" ? "异常" : "离线";
}

// 加载设备
async function loadDevices() {
  loading.value = true;
  try {
    const result = await DeviceAPI.getList(queryFormData);
    devices.value = result.data.data?.items || [];
    deviceTagsMap.value = {};
  } finally {
    loading.value = false;
  }
}

// 查询
function handleQuery() {
  loadDevices();
}

// 重置查询
function handleResetQuery() {
  queryFormRef.value?.resetFields();
  loadDevices();
}

// 展开行处理
const deviceTagsMap = ref<Record<number, TagPoint[]>>({});
const expandedRowLoading = ref<Record<number, boolean>>({});

async function handleExpand(row: Device, expandedRows: Device[]) {
  const isExpanded = expandedRows.some((r) => r.id === row.id);
  if (isExpanded && !deviceTagsMap.value[row.id]) {
    expandedRowLoading.value[row.id] = true;
    try {
      const result = await DeviceAPI.getTags(row.id);
      deviceTagsMap.value[row.id] = result.data.data?.items || [];
    } finally {
      expandedRowLoading.value[row.id] = false;
    }
  }
}

// ========== 设备弹窗 ==========
const deviceDialogVisible = ref(false);
const deviceDialogTitle = ref("");
const isEditDevice = ref(false);
const editDeviceId = ref<number | null>(null);
const deviceSubmitLoading = ref(false);
const deviceFormRef = ref();

const deviceFormData = reactive({
  name: "",
  code: "",
  group_name: "",
  connection_type: "TCP" as "TCP" | "RTU_OVER_TCP",
  host: "",
  port: 502,
  slave_id: 1,
  description: "",
});

const deviceRules = {
  name: [{ required: true, message: "请输入设备名称", trigger: "blur" }],
  code: [{ required: true, message: "请输入设备编码", trigger: "blur" }],
  host: [{ required: true, message: "请输入IP地址", trigger: "blur" }],
  port: [{ required: true, message: "请输入端口", trigger: "blur" }],
};

function handleOpenDeviceDialog(device?: Device) {
  if (device) {
    isEditDevice.value = true;
    editDeviceId.value = device.id;
    deviceDialogTitle.value = "编辑设备";
    Object.assign(deviceFormData, {
      name: device.name,
      code: device.code,
      group_name: device.group_name || "",
      connection_type: device.connection_type,
      host: device.host,
      port: device.port,
      slave_id: device.slave_id,
      description: device.description || "",
    });
  } else {
    isEditDevice.value = false;
    editDeviceId.value = null;
    deviceDialogTitle.value = "新增设备";
    Object.assign(deviceFormData, {
      name: "",
      code: "",
      group_name: "",
      connection_type: "TCP",
      host: "",
      port: 502,
      slave_id: 1,
      description: "",
    });
  }
  deviceDialogVisible.value = true;
}

function handleCloseDeviceDialog() {
  deviceFormRef.value?.resetFields();
}

async function handleDeviceSubmit() {
  try {
    await deviceFormRef.value?.validate();
    deviceSubmitLoading.value = true;

    if (isEditDevice.value && editDeviceId.value) {
      await DeviceAPI.update(editDeviceId.value, deviceFormData);
    } else {
      await DeviceAPI.create(deviceFormData);
    }

    deviceDialogVisible.value = false;
    loadDevices();
  } finally {
    deviceSubmitLoading.value = false;
  }
}

async function handleDeleteDevice(deviceId: number) {
  await DeviceAPI.delete([deviceId]);
  loadDevices();
}

// ========== 点位抽屉 ==========
const tagDrawerVisible = ref(false);
const currentDevice = ref<Device | null>(null);
const tagTableData = ref<TagPoint[]>([]);
const tagLoading = ref(false);
const tagQueryFormData = reactive({
  name: undefined as string | undefined,
  register_type: undefined as string | undefined,
});
const tagPagination = reactive({
  page_no: 1,
  pageSize: 10,
  total: 0,
});

async function handleOpenTagDrawer(device: Device) {
  currentDevice.value = device;
  tagDrawerVisible.value = true;
  tagQueryFormData.name = undefined;
  tagQueryFormData.register_type = undefined;
  tagPagination.page_no = 1;
  await loadTags();
}

async function loadTags() {
  if (!currentDevice.value) return;
  tagLoading.value = true;
  try {
    const result = await DeviceAPI.getTags(currentDevice.value.id, {
      name: tagQueryFormData.name,
      register_type: tagQueryFormData.register_type,
      page_no: tagPagination.page_no,
      page_size: tagPagination.pageSize,
    });
    tagTableData.value = result.data.data?.items || [];
    tagPagination.total = result.data.data?.total || 0;
  } finally {
    tagLoading.value = false;
  }
}

function handleTagQuery() {
  tagPagination.page_no = 1;
  loadTags();
}

function handleTagResetQuery() {
  tagQueryFormData.name = undefined;
  tagQueryFormData.register_type = undefined;
  tagPagination.page_no = 1;
  loadTags();
}

function handleTagSizeChange(size: number) {
  tagPagination.pageSize = size;
  loadTags();
}

function handleTagCurrentChange(page: number) {
  tagPagination.page_no = page;
  loadTags();
}

// ========== 点位弹窗 ==========
const tagDialogVisible = ref(false);
const tagDialogTitle = ref("");
const isEditTag = ref(false);
const editTagId = ref<number | null>(null);
const tagSubmitLoading = ref(false);
const tagFormRef = ref();

const tagFormData = reactive({
  name: "",
  code: "",
  address: 0,
  register_type: "holding" as "holding" | "input" | "coil" | "discrete",
  data_type: "INT16" as "INT16" | "UINT16" | "INT32" | "UINT32" | "FLOAT" | "BOOL",
  min_value: 0,
  max_value: 100,
  unit: "",
  scale_factor: 1,
  offset: 0,
  access_type: "READ_WRITE" as "READ" | "WRITE" | "READ_WRITE",
  requires_confirmation: false,
});

const tagRules = {
  name: [{ required: true, message: "请输入点位名称", trigger: "blur" }],
  code: [{ required: true, message: "请输入点位编码", trigger: "blur" }],
  address: [{ required: true, message: "请输入寄存器地址", trigger: "blur" }],
};

function handleOpenTagDialog(tag?: TagPoint) {
  if (tag) {
    isEditTag.value = true;
    editTagId.value = tag.id;
    tagDialogTitle.value = "编辑点位";
    Object.assign(tagFormData, {
      name: tag.name,
      code: tag.code,
      address: tag.address,
      register_type: tag.register_type,
      data_type: tag.data_type,
      min_value: tag.min_value,
      max_value: tag.max_value,
      unit: tag.unit || "",
      scale_factor: tag.scale_factor,
      offset: tag.offset,
      access_type: tag.access_type,
      requires_confirmation: tag.requires_confirmation,
    });
  } else {
    isEditTag.value = false;
    editTagId.value = null;
    tagDialogTitle.value = "新增点位";
    Object.assign(tagFormData, {
      name: "",
      code: "",
      address: 0,
      register_type: "holding",
      data_type: "INT16",
      min_value: 0,
      max_value: 100,
      unit: "",
      scale_factor: 1,
      offset: 0,
      access_type: "READ_WRITE",
      requires_confirmation: false,
    });
  }
  tagDialogVisible.value = true;
}

function handleCloseTagDialog() {
  tagFormRef.value?.resetFields();
}

async function handleTagSubmit() {
  try {
    await tagFormRef.value?.validate();
    tagSubmitLoading.value = true;

    if (isEditTag.value && editTagId.value) {
      await DeviceAPI.updateTag(editTagId.value, tagFormData);
    } else if (currentDevice.value) {
      await DeviceAPI.createTag(currentDevice.value.id, tagFormData);
    }

    tagDialogVisible.value = false;
    loadTags();
  } finally {
    tagSubmitLoading.value = false;
  }
}

async function handleDeleteTag(tagId: number) {
  await DeviceAPI.deleteTag([tagId]);
  loadTags();
}

// 初始化
onMounted(() => {
  loadDevices();
});
</script>

<style lang="scss" scoped>
.search-container {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.drawer-search-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.pagination-container {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>

<!-- Modbus 操作日志页面 -->
<template>
  <div class="app-container">
    <el-card class="data-table">
      <template #header>
        <div class="card-header">
          <span>操作日志</span>
        </div>
        <!-- 筛选区域 -->
        <div class="search-container">
          <el-form :inline="true" label-suffix=":">
            <el-form-item label="设备">
              <el-select
                v-model="filterParams.device_id"
                placeholder="全部设备"
                style="width: 150px"
                clearable
              >
                <el-option v-for="d in devices" :key="d.id" :value="d.id" :label="d.name" />
              </el-select>
            </el-form-item>
            <el-form-item label="操作类型">
              <el-select
                v-model="filterParams.action"
                placeholder="全部类型"
                style="width: 100px"
                clearable
              >
                <el-option value="READ" label="读取" />
                <el-option value="WRITE" label="写入" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select
                v-model="filterParams.status"
                placeholder="全部状态"
                style="width: 100px"
                clearable
              >
                <el-option value="success" label="成功" />
                <el-option value="failed" label="失败" />
                <el-option value="pending" label="待执行" />
                <el-option value="cancelled" label="已取消" />
              </el-select>
            </el-form-item>
            <el-form-item label="时间范围">
              <el-date-picker
                v-model="dateRange"
                type="datetimerange"
                range-separator="至"
                start-placeholder="开始时间"
                end-placeholder="结束时间"
                value-format="YYYY-MM-DD HH:mm:ss"
                @change="onDateChange"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" icon="Search" @click="handleQuery">查询</el-button>
              <el-button icon="Refresh" @click="resetFilter">重置</el-button>
              <el-button icon="Download" @click="exportLogs">导出</el-button>
            </el-form-item>
          </el-form>
        </div>
      </template>

      <!-- 表格区域 -->
      <div class="data-table__content">
        <el-table v-loading="loading" :data="logs" border stripe>
          <template #empty>
            <el-empty :image-size="80" description="暂无数据" />
          </template>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="device_id" label="设备ID" width="100">
            <template #default="{ row }">
              {{ row.device_id || "-" }}
            </template>
          </el-table-column>
          <el-table-column prop="tag_id" label="点位ID" width="100">
            <template #default="{ row }">
              {{ row.tag_id || "-" }}
            </template>
          </el-table-column>
          <el-table-column prop="action" label="操作类型" width="100">
            <template #default="{ row }">
              <el-tag :type="getActionType(row.action)" size="small">
                {{ getActionText(row.action) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="request_value" label="请求值" width="100">
            <template #default="{ row }">
              {{ row.request_value ?? "-" }}
            </template>
          </el-table-column>
          <el-table-column prop="actual_value" label="实际值" width="100">
            <template #default="{ row }">
              {{ row.actual_value ?? "-" }}
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="execution_time" label="执行时间" width="120">
            <template #default="{ row }">
              <span v-if="row.execution_time">{{ row.execution_time.toFixed(2) }} ms</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="created_time" label="创建时间" min-width="160">
            <template #default="{ row }">
              {{ formatTime(row.created_time) }}
            </template>
          </el-table-column>
          <el-table-column fixed="right" label="操作" align="center" width="100">
            <template #default="{ row }">
              <el-button type="primary" size="small" link @click="showDetail(row.id)">
                详情
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 分页 -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="pagination.page_no"
            v-model:page-size="pagination.pageSize"
            :page-sizes="pagination.pageSizes"
            :total="pagination.total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </el-card>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailDrawerVisible" title="日志详情" direction="rtl" size="500px">
      <div v-loading="detailLoading">
        <el-descriptions v-if="currentLog" :column="1" border size="small">
          <el-descriptions-item label="日志ID">
            {{ currentLog.id }}
          </el-descriptions-item>
          <el-descriptions-item label="设备ID">
            {{ currentLog.device_id || "-" }}
          </el-descriptions-item>
          <el-descriptions-item label="点位ID">
            {{ currentLog.tag_id || "-" }}
          </el-descriptions-item>
          <el-descriptions-item label="操作类型">
            <el-tag :type="getActionType(currentLog.action)" size="small">
              {{ getActionText(currentLog.action) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="请求值">
            {{ currentLog.request_value ?? "-" }}
          </el-descriptions-item>
          <el-descriptions-item label="实际值">
            {{ currentLog.actual_value ?? "-" }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentLog.status)" size="small">
              {{ getStatusText(currentLog.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="执行时间">
            {{ currentLog.execution_time ? `${currentLog.execution_time.toFixed(2)} ms` : "-" }}
          </el-descriptions-item>
          <el-descriptions-item label="重试次数">
            {{ currentLog.retry_count }}
          </el-descriptions-item>
          <el-descriptions-item label="需要确认">
            <el-tag :type="currentLog.confirmation_required ? 'warning' : 'info'" size="small">
              {{ currentLog.confirmation_required ? "是" : "否" }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatTime(currentLog.created_time) }}
          </el-descriptions-item>
          <el-descriptions-item label="执行时间">
            {{ formatTime(currentLog.executed_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="用户输入">
            <div class="detail-content">{{ currentLog.user_input || "-" }}</div>
          </el-descriptions-item>
          <el-descriptions-item label="AI推理">
            <div class="detail-content">{{ currentLog.ai_reasoning || "-" }}</div>
          </el-descriptions-item>
          <el-descriptions-item v-if="currentLog.error_message" label="错误信息">
            <div class="error-text">{{ currentLog.error_message }}</div>
          </el-descriptions-item>
        </el-descriptions>
        <el-empty v-else description="加载失败" :image-size="60" />
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import dayjs from "dayjs";
import { Icon } from "@iconify/vue";
import LogAPI, { type CommandLog } from "@/api/module_modbus/log";
import DeviceAPI from "@/api/module_modbus/device";
import type { Device } from "@/api/module_modbus";

const logs = ref<CommandLog[]>([]);
const devices = ref<Device[]>([]);
const loading = ref(false);

const filterParams = reactive({
  device_id: undefined as number | undefined,
  action: undefined as string | undefined,
  status: undefined as string | undefined,
  start_time: undefined as string | undefined,
  end_time: undefined as string | undefined,
});

const dateRange = ref<[Date, Date] | null>(null);

const pagination = reactive({
  page_no: 1,
  pageSize: 20,
  total: 0,
  pageSizes: [10, 20, 50, 100],
});

// 状态颜色
function getStatusType(status: string): "primary" | "success" | "danger" | "warning" | "info" {
  const types: Record<string, "primary" | "success" | "danger" | "warning" | "info"> = {
    success: "success",
    failed: "danger",
    pending: "warning",
    cancelled: "info",
  };
  return types[status] || "info";
}

// 状态文本
function getStatusText(status: string): string {
  const texts: Record<string, string> = {
    success: "成功",
    failed: "失败",
    pending: "待执行",
    cancelled: "已取消",
  };
  return texts[status] || status;
}

// 操作类型文本
function getActionText(action: string): string {
  return action === "READ" ? "读取" : "写入";
}

// 操作类型颜色
function getActionType(action: string): "primary" | "success" {
  return action === "READ" ? "primary" : "success";
}

// 详情抽屉
const detailDrawerVisible = ref(false);
const currentLog = ref<CommandLog | null>(null);
const detailLoading = ref(false);

async function showDetail(logId: number) {
  detailLoading.value = true;
  detailDrawerVisible.value = true;
  try {
    const result = await LogAPI.getDetail(logId);
    currentLog.value = result.data.data || null;
  } catch {
    currentLog.value = null;
  } finally {
    detailLoading.value = false;
  }
}

function formatTime(time?: string): string {
  if (!time) return "-";
  return dayjs(time).format("YYYY-MM-DD HH:mm:ss");
}

async function loadLogs() {
  loading.value = true;
  try {
    const result = await LogAPI.getList({
      ...filterParams,
      page_no: pagination.page_no,
      page_size: pagination.pageSize,
    });
    logs.value = result.data.data?.items || [];
    pagination.total = result.data.data?.total || 0;
  } finally {
    loading.value = false;
  }
}

async function loadDevices() {
  try {
    const result = await DeviceAPI.getList();
    devices.value = result.data.data?.items || [];
  } catch {
    devices.value = [];
  }
}

function resetFilter() {
  filterParams.device_id = undefined;
  filterParams.action = undefined;
  filterParams.status = undefined;
  filterParams.start_time = undefined;
  filterParams.end_time = undefined;
  dateRange.value = null;
  pagination.page_no = 1;
  loadLogs();
}

function onDateChange(dates: [Date, Date] | null) {
  if (dates) {
    filterParams.start_time = dayjs(dates[0]).toISOString();
    filterParams.end_time = dayjs(dates[1]).toISOString();
  } else {
    filterParams.start_time = undefined;
    filterParams.end_time = undefined;
  }
}

function handleQuery() {
  pagination.page_no = 1;
  loadLogs();
}

function handleSizeChange(size: number) {
  pagination.pageSize = size;
  pagination.page_no = 1;
  loadLogs();
}

function handleCurrentChange(page: number) {
  pagination.page_no = page;
  loadLogs();
}

function exportLogs() {
  const headers = [
    "ID",
    "设备ID",
    "点位ID",
    "操作",
    "请求值",
    "实际值",
    "状态",
    "执行时间(ms)",
    "创建时间",
  ];
  const rows = logs.value.map((log) => [
    log.id,
    log.device_id || "",
    log.tag_id || "",
    log.action,
    log.request_value ?? "",
    log.actual_value ?? "",
    log.status,
    log.execution_time ?? "",
    formatTime(log.created_time),
  ]);

  const csvContent = [headers.join(","), ...rows.map((row) => row.join(","))].join("\n");

  const blob = new Blob([`\uFEFF${csvContent}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `modbus_logs_${dayjs().format("YYYYMMDD_HHmmss")}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

onMounted(() => {
  loadDevices();
  loadLogs();
});
</script>

<style scoped lang="scss">
.search-container {
  margin-bottom: 16px;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.error-text {
  color: var(--el-color-danger);
}

.detail-content {
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 200px;
  overflow-y: auto;
}
</style>

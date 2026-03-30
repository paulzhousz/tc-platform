<!-- Modbus 控制页面 - AI 助手对话界面 -->
<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { marked } from "marked";
import DOMPurify from "dompurify";
import { useModbusStore, type ChatSession } from "@/store/modules/modbus.store";
import { DeviceAPI, ControlAPI } from "@/api/module_modbus";
import type { Device, TagPoint, ActionStep, ModbusConfig } from "@/api/module_modbus";
import { useModbusWs } from "@/composables/modbus/use-modbus-ws";
import { useFunASRWs } from "@/composables/modbus/use-funasr-ws";
import { useTypewriter } from "@/composables/modbus/use-typewriter";
import { Icon } from "@iconify/vue";

const modbusStore = useModbusStore();

// 连接状态
const connected = ref(false);
const connecting = ref(false);
const disconnecting = ref(false);

// WebSocket 连接
const { connect: connectWs, disconnect: disconnectWs } = useModbusWs();

// 打字机效果
const { cursorVisible } = useTypewriter(() => modbusStore.chatLoading);

// 设备树数据
const selectedKeys = ref<number[]>([]);

const treeData = computed(() => {
  const groups = modbusStore.deviceTree;
  return Object.entries(groups).map(([groupName, devices], index) => ({
    id: `group-${index}`,
    label: groupName,
    children: devices.map((d) => ({
      id: d.id,
      label: d.name,
      device_status: d.device_status,
    })),
  }));
});

// 对话相关
const inputMessage = ref("");
const messageListRef = ref<HTMLElement | null>(null);
const expandedReasonings = ref<number[]>([]);
const expandedSteps = ref<Set<string>>(new Set());

// Modbus 配置（从后端获取）
const modbusConfig = ref<ModbusConfig>({
  modbus_llm_model_name: "Qwen/Qwen3-8B",
  modbus_llm_temperature: 0,
  modbus_llm_session_ttl_minutes: 10,
  modbus_llm_max_history_turns: 20,
  modbus_retry_enabled: true,
  modbus_retry_times: 3,
  modbus_retry_interval: 1.0,
  modbus_poll_enabled: true,
  modbus_poll_interval: 5,
  modbus_pending_expire_minutes: 10,
  // 注意: modbus_funasr_mode 参数目前未使用，mode 在 useFunASRWs 中硬编码为 "2pass-offline"
  // 如需动态配置，需给 useFunASRWs 添加 mode 参数
  modbus_funasr_mode: "2pass-offline",
  modbus_silence_threshold: 0.03,
  modbus_silence_duration: 5,
  // 聊天历史配置
  modbus_chat_save_min_messages: 2,
});

// 语音输入相关
const {
  isConnected: voiceConnected,
  isRecording: voiceRecording,
  tempResult: voiceTempResult,
  startRecording: startVoiceRecording,
  stopRecording: stopVoiceRecording,
  connect: connectVoiceService,
  updateSilenceConfig,
} = useFunASRWs({
  onResult: (text, isFinal) => {
    if (isFinal && text) {
      inputMessage.value = text;
    }
  },
  onError: (error) => {
    ElMessage.error(error.message || "语音输入错误");
  },
  // 使用配置值
  silenceThreshold: modbusConfig.value.modbus_silence_threshold,
  silenceDuration: modbusConfig.value.modbus_silence_duration,
});

// 快捷指令
const quickCommands = ref<{ label: string; text: string }[]>([]);

// 设备状态抽屉
const deviceDrawerVisible = ref(false);
const selectedDevice = ref<Device | null>(null);
const deviceTags = ref<TagPoint[]>([]);
const tagLoading = ref(false);
const deviceConnecting = ref(false);
const deviceDisconnecting = ref(false);
const expandedGroupKey = ref<string>();

// 按寄存器类型分组的点位
interface TagGroup {
  key: string;
  label: string;
  tags: TagPoint[];
}

const groupedTags = computed<TagGroup[]>(() => {
  const typeLabels: Record<string, string> = {
    holding: "保持寄存器",
    input: "输入寄存器",
    coil: "线圈",
    discrete: "离散输入",
  };

  const groups: Record<string, TagPoint[]> = {
    holding: [],
    input: [],
    coil: [],
    discrete: [],
  };

  deviceTags.value.forEach((tag) => {
    if (groups[tag.register_type]) {
      groups[tag.register_type].push(tag);
    }
  });

  return Object.entries(groups).map(([key, tags]) => ({
    key,
    label: typeLabels[key] || key,
    tags,
  }));
});

// 聊天历史侧边栏
const showHistorySidebar = ref(false);
const selectedHistorySession = ref<ChatSession | null>(null);
const confirmLoadSession = ref<ChatSession | null>(null);
const confirmLoadDialogVisible = ref(false);

// Markdown 渲染
function renderMarkdown(content: string): string {
  if (!content) return "";
  const rawHtml = marked(content) as string;
  return DOMPurify.sanitize(rawHtml);
}

// 连接/断开设备
async function handleConnect() {
  if (connecting.value) return;

  connecting.value = true;
  try {
    const result = await ControlAPI.connect();
    const data = result.data.data;
    if (!data) return;

    const results = data.results || [];
    const failedCount = results.filter((r: { success: boolean }) => !r.success)
      .length;

    if (failedCount === results.length) {
      return;
    }

    // 消息由全局拦截器显示

    // 立即更新成功连接的设备状态（参考 handleConnectDevice 的模式）
    // 避免 loadDevices() 的竞态条件：WebSocket 推送可能先到达，loadDevices 返回陈旧数据覆盖正确状态
    const successResults = results.filter((r: { success: boolean; device_id: number }) => r.success);
    for (const r of successResults) {
      modbusStore.updateDeviceStatus(r.device_id, "online", new Date().toISOString());
    }

    connected.value = true;
    connectWs();
    // 移除 loadDevices() 调用，依赖 WebSocket 推送和手动更新保持状态一致
    // 如果需要获取最新设备列表，应该在 WebSocket 推送完成后或延迟一段时间再刷新
    await modbusStore.loadAllDeviceTagPoints();
  } catch {
    // 错误已在 request 中处理
  } finally {
    connecting.value = false;
  }
}

async function handleDisconnect() {
  if (disconnecting.value || !connected.value) return;

  disconnecting.value = true;
  try {
    // 保存当前对话（如果消息数达到阈值）
    const minMessages = modbusConfig.value.modbus_chat_save_min_messages;
    if (modbusStore.messages.length >= minMessages) {
      const onlineDevs = modbusStore.onlineDevices;
      await modbusStore.saveChatHistory(
        onlineDevs.length,
        onlineDevs.map((d) => d.name)
      );
    }

    await ControlAPI.disconnect();

    // 手动更新所有设备状态为 offline
    for (const device of modbusStore.devices) {
      modbusStore.updateDeviceStatus(device.id, "offline", undefined);
    }

    connected.value = false;
    // 不调用 disconnectWs()，保持 WebSocket 连接
    // 页面卸载时会自动断开（onUnmounted）
    modbusStore.clearMessages();
  } catch {
    // 错误已由全局拦截器处理
  } finally {
    disconnecting.value = false;
  }
}

// 单个设备连接
async function handleConnectDevice(device: Device) {
  if (deviceConnecting.value || device.device_status === "online") return;

  deviceConnecting.value = true;
  try {
    const result = await ControlAPI.connect([device.id]);
    const data = result.data.data;
    if (!data) return;

    const results = data.results || [];
    const deviceResult = results.find(
      (r: { device_id: number }) => r.device_id === device.id
    );

    if (deviceResult?.success) {
      // 立即更新 store 中的设备状态，确保 UI 即时响应
      // WebSocket 推送会作为后续同步的保障
      modbusStore.updateDeviceStatus(device.id, "online", new Date().toISOString());

      // 同步更新 selectedDevice 引用，确保抽屉显示正确状态
      if (selectedDevice.value?.id === device.id) {
        selectedDevice.value = {
          ...selectedDevice.value,
          device_status: "online",
          last_seen: new Date().toISOString(),
        };
      }

      if (!connected.value) {
        connected.value = true;
        connectWs();
      }

      // 刷新点位数据
      if (selectedDevice.value?.id === device.id) {
        const tagResult = await DeviceAPI.getTags(device.id);
        deviceTags.value = tagResult.data.data?.items || [];
      }
    }
  } catch {
    // 错误已处理
  } finally {
    deviceConnecting.value = false;
  }
}

// 单个设备断开
async function handleDisconnectDevice(device: Device) {
  if (deviceDisconnecting.value || device.device_status !== "online") return;

  deviceDisconnecting.value = true;
  try {
    const result = await ControlAPI.disconnect([device.id]);
    if (result.data.data) {
      // 立即更新 store 中的设备状态
      modbusStore.updateDeviceStatus(device.id, "offline", undefined);

      // 同步更新 selectedDevice 引用，确保抽屉显示正确状态
      if (selectedDevice.value?.id === device.id) {
        selectedDevice.value = {
          ...selectedDevice.value,
          device_status: "offline",
          last_seen: undefined,
        };
      }

      const hasOtherOnline = modbusStore.devices.some(
        (d) => d.id !== device.id && d.device_status === "online"
      );
      if (!hasOtherOnline) {
        connected.value = false;
        // 不调用 disconnectWs()，保持 WebSocket 连接
      }
    }
  } catch {
    // 错误已处理
  } finally {
    deviceDisconnecting.value = false;
  }
}

// 初始化时检查连接状态
async function checkConnectionStatus(): Promise<boolean> {
  try {
    const result = await ControlAPI.getConnectionStatus();
    const status = result.data.data || [];
    const hasConnected = status.some(
      (s: { connected: boolean }) => s.connected
    );
    if (hasConnected) {
      connected.value = true;
    } else {
      modbusStore.devices.forEach((d) => {
        d.device_status = "offline";
      });
    }
    return hasConnected;
  } catch {
    modbusStore.devices.forEach((d) => {
      d.device_status = "offline";
    });
    return false;
  }
}

// 显示设备状态
async function showDeviceStatus(deviceId: number) {
  const device = modbusStore.devices.find((d) => d.id === deviceId);
  if (!device) return;

  selectedDevice.value = device;
  deviceDrawerVisible.value = true;
  expandedGroupKey.value = undefined;

  tagLoading.value = true;
  try {
    const result = await DeviceAPI.getTags(deviceId);
    deviceTags.value = result.data.data?.items || [];
  } catch {
    deviceTags.value = [];
  } finally {
    tagLoading.value = false;
  }
}

// 分组展开时刷新点位数据
async function handleGroupExpand(activeKey: string | string[]) {
  const key = Array.isArray(activeKey) ? activeKey[0] : activeKey;

  if (key && selectedDevice.value && selectedDevice.value.device_status === "online") {
    tagLoading.value = true;
    try {
      const result = await DeviceAPI.getTags(selectedDevice.value.id);
      deviceTags.value = result.data.data?.items || [];
    } catch {
      // 忽略错误
    } finally {
      tagLoading.value = false;
    }
  }

  expandedGroupKey.value = key;
}

// 设备树选择
function onDeviceSelect(data: { id: number; label: string; device_status?: string }) {
  if (data.device_status) {
    selectedKeys.value = [data.id];
    const device = modbusStore.devices.find((d) => d.id === data.id);
    if (device) {
      inputMessage.value = `[设备: ${device.name}] `;
    }
  }
}

// 发送消息
async function sendMessage() {
  const content = inputMessage.value.trim();
  if (!content || modbusStore.chatLoading) return;

  inputMessage.value = "";
  await nextTick();

  try {
    await modbusStore.sendMessageStream(content);
    scrollToBottom();
  } catch {
    ElMessage.error("发送失败");
  }
}

// 快捷发送
function quickSend(text: string) {
  inputMessage.value = text;
  sendMessage();
}

// 语音输入切换
async function toggleVoiceRecording() {
  if (voiceRecording.value) {
    stopVoiceRecording();
  } else {
    if (!voiceConnected.value) {
      const connected = await connectVoiceService();
      if (!connected) {
        ElMessage.error("语音服务不可用");
        return;
      }
    }
    const success = await startVoiceRecording();
    if (!success) {
      ElMessage.error("无法访问麦克风");
    }
  }
}

// 输入框回车
function onInputEnter(e: KeyboardEvent) {
  if (!e.shiftKey) {
    e.preventDefault();
    e.stopPropagation();
    sendMessage();
  }
}

// 切换推理展开
function toggleReasoning(index: number) {
  const i = expandedReasonings.value.indexOf(index);
  if (i > -1) {
    expandedReasonings.value.splice(i, 1);
  } else {
    expandedReasonings.value.push(index);
  }
}

// 获取步骤图标
function getStepIcon(tool: string): string {
  const icons: Record<string, string> = {
    search_tag_mapping: "🔍",
    read_plc: "📖",
    write_plc: "✏️",
    adjust_plc: "🔧",
  };
  return icons[tool] || "⚡";
}

// 获取状态信息
function getStatusText(status: string): string {
  const texts: Record<string, string> = {
    online: "在线",
    offline: "离线",
    error: "异常",
  };
  return texts[status] || status;
}

function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    online: "#52c41a",
    offline: "#999",
    error: "#ff4d4f",
  };
  return colors[status] || "#999";
}

function getStatusType(status: string): "" | "success" | "danger" | "warning" {
  const types: Record<string, "" | "success" | "danger" | "warning"> = {
    online: "success",
    offline: "",
    error: "danger",
  };
  return types[status] || "";
}

// 获取 ActionStep 状态信息
function getActionStatusIcon(status?: string): string {
  const icons: Record<string, string> = {
    running: "mdi:loading",
    success: "mdi:check-circle",
    failed: "mdi:close-circle",
    pending: "mdi:clock-outline",
    cancelled: "mdi:minus-circle",
  };
  return icons[status || "running"] || "mdi:loading";
}

function getActionStatusColor(status?: string): string {
  const colors: Record<string, string> = {
    running: "#1890ff",
    success: "#52c41a",
    failed: "#ff4d4f",
    pending: "#faad14",
    cancelled: "#8c8c8c",
  };
  return colors[status || "running"] || "#8c8c8c";
}

function getActionStatusText(status?: string): string {
  const texts: Record<string, string> = {
    running: "执行中",
    success: "成功",
    failed: "失败",
    pending: "等待中",
    cancelled: "已取消",
  };
  return texts[status || "running"] || status || "";
}

// 切换步骤展开状态
function toggleStep(msgIndex: number, stepIndex: number) {
  const key = `${msgIndex}-${stepIndex}`;
  if (expandedSteps.value.has(key)) {
    expandedSteps.value.delete(key);
  } else {
    expandedSteps.value.add(key);
  }
}

function isStepExpanded(msgIndex: number, stepIndex: number): boolean {
  return expandedSteps.value.has(`${msgIndex}-${stepIndex}`);
}

// 获取工具名称显示
function getToolDisplayName(tool: string): string {
  const names: Record<string, string> = {
    search_device: "搜索设备",
    search_tag_mapping: "搜索点位",
    read_plc: "读取PLC",
    write_plc: "写入PLC",
    adjust_plc: "调整参数",
    confirm_operation: "确认操作",
    cancel_operation: "取消操作",
  };
  return names[tool] || tool;
}

// 格式化时间
function formatTime(time: string): string {
  return new Date(time).toLocaleString("zh-CN");
}

function formatMessageTime(timestamp?: string): string {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();

  if (isToday) {
    return date.toLocaleTimeString("zh-CN", {
      hour: "2-digit",
      minute: "2-digit",
    });
  }
  return date.toLocaleDateString("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight;
    }
  });
}

// 复制消息
async function copyMessage(content: string) {
  try {
    await navigator.clipboard.writeText(content);
    ElMessage.success("已复制");
  } catch {
    ElMessage.error("复制失败");
  }
}

// 重新生成消息
function regenerateMessage(index: number) {
  for (let i = index - 1; i >= 0; i--) {
    if (modbusStore.messages[i].role === "user") {
      const userContent = modbusStore.messages[i].content;
      modbusStore.messages.splice(i);
      inputMessage.value = userContent;
      sendMessage();
      return;
    }
  }
}

// 停止生成
function stopGeneration() {
  modbusStore.abortGeneration();
  ElMessage.info("已停止");
}

// 新建对话
async function newChat() {
  const minMessages = modbusConfig.value.modbus_chat_save_min_messages;

  // 检查是否需要保存当前对话
  if (modbusStore.messages.length >= minMessages) {
    // 获取在线设备信息
    const onlineDevs = modbusStore.onlineDevices;
    const deviceCount = onlineDevs.length;
    const deviceNames = onlineDevs.map((d) => d.name);

    // 保存当前对话
    const result = await modbusStore.saveChatHistory(deviceCount, deviceNames);
    if (result.success) {
      ElMessage.success("对话已保存");
    }
  }

  modbusStore.clearMessages();
  ElMessage.success("已创建新对话");
}

// 导出对话
function exportChat() {
  const messages = modbusStore.messages.map((msg) => ({
    role: msg.role === "user" ? "用户" : "AI助手",
    content: msg.content,
    time: msg.timestamp,
  }));

  const exportData = {
    title: "AI助手对话记录",
    exportTime: new Date().toLocaleString("zh-CN"),
    messages,
  };

  const blob = new Blob([JSON.stringify(exportData, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `chat-export-${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
  ElMessage.success("导出成功");
}

// 监听消息变化自动滚动
watch(
  () => modbusStore.messages.length,
  () => {
    scrollToBottom();
  }
);

watch(
  () => modbusStore.messages.map((m) => m.content).join(""),
  () => {
    scrollToBottom();
  }
);

// 聊天历史相关方法
function toggleHistorySidebar() {
  showHistorySidebar.value = !showHistorySidebar.value;
}

function onHistoryClick(session: ChatSession) {
  if (modbusStore.messages.length > 0) {
    confirmLoadSession.value = session;
    confirmLoadDialogVisible.value = true;
  } else {
    loadHistorySession(session);
  }
}

async function confirmLoadHistory() {
  if (confirmLoadSession.value) {
    await loadHistorySession(confirmLoadSession.value);
    confirmLoadSession.value = null;
    confirmLoadDialogVisible.value = false;
  }
}

function cancelLoadHistory() {
  confirmLoadSession.value = null;
  confirmLoadDialogVisible.value = false;
}

async function loadHistorySession(session: ChatSession) {
  await modbusStore.loadChatFromHistory(session.sessionId);
  selectedHistorySession.value = session;
  scrollToBottom();
}

async function deleteHistorySession(sessionId: string) {
  await modbusStore.deleteChatHistory(sessionId);
  if (selectedHistorySession.value?.sessionId === sessionId) {
    selectedHistorySession.value = null;
  }
  ElMessage.success("已删除");
}

// 加载快捷指令
async function loadQuickCommands() {
  try {
    const result = await ControlAPI.getQuickCommands();
    if (result.data.data?.quick_commands) {
      quickCommands.value = result.data.data.quick_commands.map(
        (cmd: { label: { zh: string }; text: { zh: string } }) => ({
          label: cmd.label.zh,
          text: cmd.text.zh,
        })
      );
    }
  } catch {
    quickCommands.value = [
      { label: "查看状态", text: "查看所有设备状态" },
      { label: "读取温度", text: "读取温度值" },
      { label: "设置频率", text: "设置频率为" },
    ];
  }
}

// 加载 Modbus 配置
async function loadModbusConfig() {
  try {
    const result = await ControlAPI.getConfig();
    if (result.data.data) {
      modbusConfig.value = result.data.data;
      // 更新语音识别的静音检测配置
      updateSilenceConfig(
        modbusConfig.value.modbus_silence_threshold,
        modbusConfig.value.modbus_silence_duration
      );
    }
  } catch (error) {
    console.error("Failed to load modbus config:", error);
  }
}

// 初始化
onMounted(async () => {
  try {
    await modbusStore.loadDevices();
    await modbusStore.loadChatHistory();
    await checkConnectionStatus();
    await loadQuickCommands();
    await loadModbusConfig();

    // 提前初始化 WebSocket 连接，确保第一次点击连接按钮时能接收后端推送
    // useModbusWs 内部会检查 token，无 token 不会连接
    connectWs();
  } catch (error) {
    console.error("Failed to initialize modbus control page:", error);
  }
});
</script>

<template>
  <div class="modbus-control-page">
    <!-- 左侧设备树 -->
    <div class="device-tree-panel">
      <div class="panel-header">
        <h3>设备列表</h3>
        <span class="online-count">
          在线: {{ modbusStore.onlineDevices.length }}/{{
            modbusStore.devices.length
          }}
        </span>
      </div>

      <!-- 未连接提示 -->
      <div v-if="!connected" class="not-connected-tip">
        <Icon icon="mdi:alert-circle-outline" class="tip-icon" />
        <span>设备未连接</span>
      </div>

      <!-- 连接控制按钮 -->
      <div class="connection-controls">
        <el-button type="primary" :loading="connecting" @click="handleConnect">
          连接设备
        </el-button>
        <el-button
          type="danger"
          :loading="disconnecting"
          :disabled="!connected"
          @click="handleDisconnect"
        >
          断开连接
        </el-button>
      </div>

      <!-- 设备树区域 -->
      <div class="device-tree-content">
        <el-tree
          v-if="treeData.length > 0"
          :data="treeData"
          :props="{ label: 'label', children: 'children' }"
          default-expand-all
          node-key="id"
          :highlight-current="true"
          @node-click="onDeviceSelect"
        >
          <template #default="{ data }">
            <span v-if="data.device_status" class="device-tree-node">
              <Icon
                :icon="data.device_status === 'online' ? 'mdi:check-circle' : 'mdi:circle-outline'"
                class="status-icon"
                :style="{ color: getStatusColor(data.device_status) }"
              />
              <span class="device-title" :class="{ offline: data.device_status !== 'online' }">
                {{ data.label }}
              </span>
              <el-button
                type="primary"
                size="small"
                link
                class="view-status-btn"
                @click.stop="showDeviceStatus(data.id)"
              >
                查看
              </el-button>
            </span>
            <span v-else>{{ data.label }}</span>
          </template>
        </el-tree>
        <el-empty v-else description="暂无设备" :image-size="60" />
      </div>

      <!-- 图例说明 -->
      <div class="legend">
        <span class="legend-item">
          <Icon icon="mdi:check-circle" class="status-icon" style="color: #52c41a" />
          <span>在线</span>
        </span>
        <span class="legend-item">
          <Icon icon="mdi:circle-outline" class="status-icon" style="color: #999" />
          <span>离线</span>
        </span>
        <span class="legend-item">
          <Icon icon="mdi:alert-circle" class="status-icon" style="color: #ff4d4f" />
          <span>异常</span>
        </span>
      </div>
    </div>

    <!-- 右侧对话区 -->
    <div class="chat-panel" :class="{ 'with-history': showHistorySidebar }">
      <!-- 对话头部 -->
      <div class="chat-header">
        <div class="chat-title">
          <Icon icon="mdi:robot-outline" class="title-icon" />
          <span>AI 助手</span>
        </div>
        <div class="chat-actions">
          <el-tooltip content="新对话" placement="bottom">
            <el-button type="primary" text @click="newChat">
              <Icon icon="mdi:plus-box-outline" />
            </el-button>
          </el-tooltip>
          <el-tooltip
            :content="showHistorySidebar ? '隐藏历史' : '历史记录'"
            placement="bottom"
          >
            <el-button
              type="primary"
              text
              :class="{ active: showHistorySidebar }"
              @click="toggleHistorySidebar"
            >
              <Icon icon="mdi:format-list-bulleted" />
            </el-button>
          </el-tooltip>
          <el-tooltip content="导出对话" placement="bottom">
            <el-button
              type="primary"
              text
              :disabled="modbusStore.messages.length === 0"
              @click="exportChat"
            >
              <Icon icon="mdi:download-outline" />
            </el-button>
          </el-tooltip>
        </div>
      </div>

      <!-- 主内容区 -->
      <div class="chat-content-wrapper">
        <!-- 对话消息列表 -->
        <div ref="messageListRef" class="message-list">
          <div
            v-for="(msg, index) in modbusStore.messages"
            :key="index"
            class="message-item"
            :class="[msg.role]"
          >
            <!-- 用户消息 -->
            <template v-if="msg.role === 'user'">
              <div class="message-avatar user-avatar">
                <Icon icon="mdi:account-circle" class="avatar-icon" />
              </div>
              <div class="message-body">
                <div class="message-header">
                  <span class="message-role">用户</span>
                  <span class="message-time">{{ formatMessageTime(msg.timestamp) }}</span>
                </div>
                <div class="message-bubble user-bubble">
                  <div class="message-content">{{ msg.content }}</div>
                </div>
              </div>
            </template>

            <!-- 助手消息 -->
            <template v-else>
              <div class="message-avatar assistant-avatar">
                <Icon icon="mdi:robot-outline" class="avatar-icon" />
              </div>
              <div class="message-body">
                <div class="message-header">
                  <span class="message-role">AI 助手</span>
                  <span class="message-time">{{ formatMessageTime(msg.timestamp) }}</span>
                </div>
                <div class="message-bubble assistant-bubble">
                  <!-- 思考中状态 -->
                  <div
                    v-if="modbusStore.chatLoading && index === modbusStore.messages.length - 1 && !msg.content && !msg.actions?.length"
                    class="thinking-indicator"
                  >
                    <span class="dot"></span>
                    <span class="dot"></span>
                    <span class="dot"></span>
                    <span class="typing-text">思考中...</span>
                  </div>

                  <!-- 推理过程 -->
                  <div v-if="msg.actions?.length" class="reasoning-panel">
                    <div class="reasoning-header" @click="toggleReasoning(index)">
                      <span class="reasoning-icon">💭</span>
                      <span>推理过程</span>
                      <span class="step-count">({{ msg.actions.length }} 步骤)</span>
                      <Icon
                        :icon="expandedReasonings.includes(index) ? 'mdi:chevron-up' : 'mdi:chevron-down'"
                        class="expand-icon"
                      />
                    </div>
                    <div v-show="expandedReasonings.includes(index)" class="reasoning-steps">
                      <div
                        v-for="(step, si) in msg.actions"
                        :key="si"
                        class="reasoning-step"
                        :class="[`status-${step.status || 'success'}`]"
                      >
                        <div class="step-header" @click="toggleStep(index, si)">
                          <span class="step-icon">{{ getStepIcon(step.tool) }}</span>
                          <span class="step-name">{{ getToolDisplayName(step.tool) }}</span>
                          <span class="step-status" :style="{ color: getActionStatusColor(step.status) }">
                            <Icon :icon="getActionStatusIcon(step.status)" class="status-icon" />
                            <span class="status-text">{{ getActionStatusText(step.status) }}</span>
                          </span>
                          <span v-if="step.duration_ms" class="step-duration">{{ step.duration_ms }}ms</span>
                          <Icon
                            :icon="isStepExpanded(index, si) ? 'mdi:chevron-up' : 'mdi:chevron-down'"
                            class="step-expand-icon"
                          />
                        </div>
                        <!-- 步骤详情 -->
                        <div v-show="isStepExpanded(index, si)" class="step-details">
                          <div v-if="step.args && Object.keys(step.args).length > 0" class="step-section">
                            <div class="step-section-title">调用参数</div>
                            <pre class="step-json">{{ JSON.stringify(step.args, null, 2) }}</pre>
                          </div>
                          <div v-if="step.data" class="step-section">
                            <div class="step-section-title">执行结果</div>
                            <div class="step-data">
                              <!-- 读取结果 -->
                              <template v-if="step.tool === 'read_plc' && step.data">
                                <div v-if="step.data.device_name" class="data-row">
                                  <span class="data-label">设备:</span>
                                  <span class="data-value">{{ step.data.device_name }}</span>
                                </div>
                                <div v-if="step.data.tag_name" class="data-row">
                                  <span class="data-label">点位:</span>
                                  <span class="data-value">{{ step.data.tag_name }}</span>
                                </div>
                                <div v-if="step.data.value !== undefined" class="data-row highlight">
                                  <span class="data-label">当前值:</span>
                                  <span class="data-value">
                                    {{ step.data.value }} {{ step.data.unit || "" }}
                                  </span>
                                </div>
                              </template>
                              <!-- 写入/调整结果 -->
                              <template v-else-if="(step.tool === 'write_plc' || step.tool === 'adjust_plc') && step.data">
                                <div v-if="step.data.device_name" class="data-row">
                                  <span class="data-label">设备:</span>
                                  <span class="data-value">{{ step.data.device_name }}</span>
                                </div>
                                <div v-if="step.data.tag_name" class="data-row">
                                  <span class="data-label">点位:</span>
                                  <span class="data-value">{{ step.data.tag_name }}</span>
                                </div>
                                <div v-if="step.data.value !== undefined" class="data-row highlight">
                                  <span class="data-label">写入值:</span>
                                  <span class="data-value">
                                    {{ step.data.value }} {{ step.data.unit || "" }}
                                  </span>
                                </div>
                              </template>
                              <!-- 其他情况 -->
                              <template v-else>
                                <pre class="step-json">{{ JSON.stringify(step.data, null, 2) }}</pre>
                              </template>
                            </div>
                          </div>
                          <!-- 错误信息 -->
                          <div v-if="step.error" class="step-error">
                            <Icon icon="mdi:alert-circle" class="error-icon" />
                            <span>{{ step.error }}</span>
                          </div>
                        </div>
                      </div>
                      <!-- 加载指示 -->
                      <div
                        v-if="modbusStore.chatLoading && index === modbusStore.messages.length - 1"
                        class="reasoning-loading"
                      >
                        <span class="dot"></span>
                        <span class="dot"></span>
                        <span class="dot"></span>
                        <span class="typing-text">执行中...</span>
                      </div>
                    </div>
                  </div>

                  <!-- 回复内容 -->
                  <div class="message-content-wrapper">
                    <div
                      v-if="msg.content"
                      class="message-content markdown-body"
                      v-html="renderMarkdown(msg.content)"
                    ></div>
                    <!-- 打字机光标 -->
                    <span
                      v-if="modbusStore.chatLoading && index === modbusStore.messages.length - 1"
                      class="typewriter-cursor"
                      :class="{ hidden: !cursorVisible }"
                    ></span>
                  </div>

                  <!-- 消息操作按钮 -->
                  <div v-if="msg.content" class="message-actions">
                    <el-tooltip content="复制" placement="bottom">
                      <el-button type="primary" size="small" text @click="copyMessage(msg.content)">
                        <Icon icon="mdi:content-copy" />
                      </el-button>
                    </el-tooltip>
                    <el-tooltip content="重新生成" placement="bottom">
                      <el-button type="primary" size="small" text @click="regenerateMessage(index)">
                        <Icon icon="mdi:refresh" />
                      </el-button>
                    </el-tooltip>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>

        <!-- 历史对话侧边栏 -->
        <Transition name="slide-fade">
          <div v-if="showHistorySidebar" class="history-sidebar">
            <div class="history-sidebar-header">
              <span class="history-title">历史记录</span>
              <el-button
                v-if="modbusStore.chatHistory.length > 0"
                size="small"
                type="danger"
                text
                @click="modbusStore.chatHistory = []"
              >
                <Icon icon="mdi:delete-outline" />
              </el-button>
            </div>
            <div v-if="modbusStore.chatHistory.length > 0" class="history-list">
              <div
                v-for="session in modbusStore.chatHistory"
                :key="session.sessionId"
                class="history-item"
                :class="{ active: selectedHistorySession?.sessionId === session.sessionId }"
                @click="onHistoryClick(session)"
              >
                <div class="history-info">
                  <div class="history-preview">{{ session.title || "AI 对话" }}</div>
                  <div class="history-meta">
                    <span class="history-time">{{ formatTime(session.startTime) }}</span>
                  </div>
                </div>
                <el-button
                  type="primary"
                  size="small"
                  text
                  class="delete-btn"
                  @click.stop="deleteHistorySession(session.sessionId)"
                >
                  <Icon icon="mdi:close" />
                </el-button>
              </div>
            </div>
            <el-empty v-else description="暂无历史记录" :image-size="60" />
          </div>
        </Transition>
      </div>

      <!-- 快捷指令栏 -->
      <div class="quick-commands">
        <el-button
          v-for="cmd in quickCommands"
          :key="cmd.text"
          size="small"
          @click="quickSend(cmd.text)"
        >
          {{ cmd.label }}
        </el-button>
      </div>

      <!-- 输入区域 -->
      <div class="input-area">
        <div class="input-wrapper">
          <el-input
            v-model="inputMessage"
            type="textarea"
            :autosize="{ minRows: 2, maxRows: 4 }"
            placeholder="输入消息，按 Enter 发送，Shift+Enter 换行"
            :disabled="modbusStore.chatLoading"
            @keydown.enter="onInputEnter"
          />
          <div class="input-actions">
            <!-- 语音输入实时结果 -->
            <div v-if="voiceRecording && voiceTempResult" class="voice-temp-result">
              {{ voiceTempResult }}
            </div>
            <!-- 语音输入按钮 -->
            <el-tooltip :content="voiceRecording ? '停止录音' : '语音输入'" placement="top">
              <el-button
                type="primary"
                text
                :class="{ 'voice-recording': voiceRecording }"
                @click="toggleVoiceRecording"
              >
                <Icon :icon="voiceRecording ? 'mdi:stop-circle' : 'mdi:microphone'" />
              </el-button>
            </el-tooltip>
          </div>
        </div>
        <div class="send-actions">
          <el-button v-if="modbusStore.chatLoading" type="danger" @click="stopGeneration">
            <Icon icon="mdi:stop" style="margin-right: 4px" />
            停止
          </el-button>
          <el-button
            v-else
            type="primary"
            :disabled="!inputMessage.trim()"
            @click="sendMessage"
          >
            <Icon icon="mdi:send" style="margin-right: 4px" />
            发送
          </el-button>
        </div>
      </div>
    </div>

    <!-- 设备状态抽屉 -->
    <el-drawer
      v-model="deviceDrawerVisible"
      title="设备状态"
      direction="rtl"
      size="400px"
    >
      <div v-if="selectedDevice" class="device-status-content">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="设备名称">
            {{ selectedDevice.name }}
          </el-descriptions-item>
          <el-descriptions-item label="设备编码">
            {{ selectedDevice.code }}
          </el-descriptions-item>
          <el-descriptions-item label="连接类型">
            {{ selectedDevice.connection_type }}
          </el-descriptions-item>
          <el-descriptions-item label="IP地址">
            {{ selectedDevice.host }}:{{ selectedDevice.port }}
          </el-descriptions-item>
          <el-descriptions-item label="从站ID">
            {{ selectedDevice.slave_id }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedDevice.device_status)">
              {{ getStatusText(selectedDevice.device_status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="最后在线">
            {{ selectedDevice.last_seen ? formatTime(selectedDevice.last_seen) : "-" }}
          </el-descriptions-item>
        </el-descriptions>

        <!-- 设备操作按钮 -->
        <div class="device-action-section">
          <el-button
            v-if="selectedDevice.device_status === 'online'"
            type="danger"
            :loading="deviceDisconnecting"
            @click="handleDisconnectDevice(selectedDevice)"
          >
            断开设备
          </el-button>
          <el-button
            v-else
            type="primary"
            :loading="deviceConnecting"
            @click="handleConnectDevice(selectedDevice)"
          >
            连接设备
          </el-button>
        </div>

        <!-- 点位列表 -->
        <div class="tag-points-section">
          <h4>点位列表</h4>
          <div v-loading="tagLoading">
            <el-collapse v-model="expandedGroupKey" accordion @change="handleGroupExpand">
              <el-collapse-item
                v-for="group in groupedTags"
                :key="group.key"
                :name="group.key"
                :title="`${group.label} (${group.tags.length})`"
              >
                <el-table
                  v-if="group.tags.length > 0"
                  :data="group.tags"
                  size="small"
                  border
                >
                  <el-table-column prop="name" label="名称" min-width="100" />
                  <el-table-column label="当前值" width="100">
                    <template #default="{ row }">
                      {{ row.current_value ?? "-" }} {{ row.unit || "" }}
                    </template>
                  </el-table-column>
                  <el-table-column prop="address" label="地址" width="80" />
                  <el-table-column prop="access_type" label="访问" width="80" />
                </el-table>
                <el-empty v-else description="暂无数据" :image-size="40" />
              </el-collapse-item>
            </el-collapse>
            <el-empty v-if="groupedTags.length === 0" description="暂无点位数据" :image-size="60" />
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 加载历史确认弹窗 -->
    <el-dialog
      v-model="confirmLoadDialogVisible"
      title="加载历史对话"
      width="400px"
      @confirm="confirmLoadHistory"
    >
      <p>加载历史对话将替换当前对话，是否继续？</p>
      <template #footer>
        <el-button @click="cancelLoadHistory">取消</el-button>
        <el-button type="primary" @click="confirmLoadHistory">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped lang="scss">
.modbus-control-page {
  display: flex;
  height: calc(100vh - 120px);
  gap: 16px;
  padding: 16px;
  background: #f5f7fa;
}

.device-tree-panel {
  width: 280px;
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    flex-shrink: 0;

    h3 {
      margin: 0;
      font-size: 16px;
    }

    .online-count {
      font-size: 12px;
      color: #666;
    }
  }

  .device-tree-node {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    width: 100%;

    .view-status-btn {
      padding: 0 4px;
      font-size: 12px;
      margin-left: auto;
    }
  }

  .device-title {
    &.offline {
      color: #999;
    }
  }

  .status-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
  }

  .device-tree-content {
    flex: 1;
    overflow-y: auto;
    min-height: 0;
  }

  .legend {
    flex-shrink: 0;
    display: flex;
    gap: 16px;
    margin-top: 16px;
    padding-top: 12px;
    border-top: 1px solid #f0f0f0;
    font-size: 12px;
    color: #666;

    .legend-item {
      display: inline-flex;
      align-items: center;
      gap: 4px;

      .status-icon {
        font-size: 14px;
      }
    }
  }
}

.connection-controls {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.not-connected-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: 6px;
  font-size: 13px;
  color: #d46b08;
  margin-bottom: 12px;

  .tip-icon {
    font-size: 18px;
    color: #fa8c16;
  }
}

.chat-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
}

.chat-content-wrapper {
  flex: 1;
  display: flex;
  min-height: 0;
  position: relative;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafbfc;
  flex-shrink: 0;

  .chat-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 500;
    color: var(--el-color-primary);

    .title-icon {
      font-size: 20px;
      color: var(--el-color-primary);
    }
  }

  .chat-actions {
    display: flex;
    gap: 4px;
  }
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: linear-gradient(to bottom, #fafbfc, #fff);
  min-width: 0;

  .message-item {
    display: flex;
    gap: 12px;
    margin-bottom: 24px;
    animation: fadeIn 0.3s ease;

    &.user {
      flex-direction: row-reverse;

      .message-body {
        align-items: flex-end;
      }

      .message-header {
        flex-direction: row-reverse;
      }
    }

    &.assistant {
      .message-body {
        align-items: flex-start;
      }
    }
  }

  .message-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    flex-shrink: 0;

    .avatar-icon {
      font-size: 22px;
      color: #fff;
    }

    &.user-avatar {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }

    &.assistant-avatar {
      background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    }
  }

  .message-body {
    display: flex;
    flex-direction: column;
    gap: 4px;
    max-width: 75%;
  }

  .message-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 0 4px;

    .message-role {
      font-size: 13px;
      font-weight: 500;
      color: #333;
    }

    .message-time {
      font-size: 12px;
      color: #999;
    }
  }

  .message-bubble {
    padding: 12px 16px;
    border-radius: 16px;
    word-break: break-word;
    position: relative;

    &.user-bubble {
      background: linear-gradient(135deg, var(--el-color-primary) 0%, var(--el-color-primary-dark-2) 100%);
      color: #fff;
      border-bottom-right-radius: 4px;
    }

    &.assistant-bubble {
      background: #f5f7fa;
      border: 1px solid #e8eaed;
      border-bottom-left-radius: 4px;
    }
  }

  .message-actions {
    display: flex;
    gap: 4px;
    margin-top: 8px;
    opacity: 0;
    transition: opacity 0.2s;
  }

  .message-bubble:hover .message-actions {
    opacity: 1;
  }
}

// 推理面板样式
.reasoning-panel {
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 13px;
  overflow: hidden;

  .reasoning-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 12px;
    cursor: pointer;
    background: #fafafa;
    user-select: none;
    transition: background 0.2s;

    &:hover {
      background: #f0f0f0;
    }

    .reasoning-icon {
      font-size: 16px;
    }

    .step-count {
      color: #999;
      font-size: 12px;
    }

    .expand-icon {
      margin-left: auto;
      font-size: 18px;
      color: #666;
    }
  }

  .reasoning-steps {
    border-top: 1px solid #e8e8e8;

    .reasoning-step {
      border-bottom: 1px solid #f0f0f0;

      &:last-child {
        border-bottom: none;
      }

      &.status-success {
        border-left: 3px solid #52c41a;
      }

      &.status-failed {
        border-left: 3px solid #ff4d4f;
      }

      &.status-pending {
        border-left: 3px solid #faad14;
      }

      &.status-running {
        border-left: 3px solid var(--el-color-primary);
      }

      .step-header {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 10px 12px;
        cursor: pointer;
        background: #fff;
        transition: background 0.2s;

        &:hover {
          background: #fafafa;
        }

        .step-icon {
          font-size: 16px;
        }

        .step-name {
          font-weight: 500;
          color: #333;
        }

        .step-status {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 12px;
        }

        .step-duration {
          margin-left: auto;
          font-size: 11px;
          color: #999;
          background: #f5f5f5;
          padding: 2px 6px;
          border-radius: 4px;
        }

        .step-expand-icon {
          font-size: 14px;
          color: #999;
        }
      }

      .step-details {
        padding: 0 12px 12px 36px;
        background: #fafbfc;

        .step-section {
          margin-top: 10px;

          .step-section-title {
            font-size: 12px;
            color: #666;
            margin-bottom: 6px;
            font-weight: 500;
          }
        }

        .step-data {
          background: #fff;
          border: 1px solid #e8e8e8;
          border-radius: 6px;
          padding: 10px 12px;

          .data-row {
            display: flex;
            align-items: center;
            padding: 4px 0;
            font-size: 13px;

            &.highlight {
              background: var(--el-color-primary-light-9);
              margin: 4px -12px;
              padding: 6px 12px;
              border-radius: 4px;

              .data-value {
                font-weight: 600;
                color: var(--el-color-primary);
              }
            }

            .data-label {
              color: #666;
              min-width: 80px;
            }

            .data-value {
              color: #333;
            }
          }
        }

        .step-json {
          background: #f5f5f5;
          border: 1px solid #e8e8e8;
          border-radius: 4px;
          padding: 8px 10px;
          font-size: 11px;
          font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
          overflow-x: auto;
          margin: 0;
          white-space: pre-wrap;
          word-break: break-all;
        }

        .step-error {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 8px 12px;
          background: #fff2f0;
          border: 1px solid #ffccc7;
          border-radius: 4px;
          color: #ff4d4f;
          font-size: 12px;
          margin-top: 10px;

          .error-icon {
            font-size: 14px;
            color: #ff4d4f;
          }
        }
      }
    }

    .reasoning-loading {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 12px;
      border-top: 1px dashed #e8e8e8;

      .typing-text {
        margin-left: 8px;
        color: #999;
        font-size: 12px;
      }
    }
  }
}

// 思考指示器
.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 16px;

  .dot {
    width: 8px;
    height: 8px;
    background: var(--el-color-primary);
    border-radius: 50%;
    animation: bounce 1.4s infinite ease-in-out both;

    &:nth-child(1) {
      animation-delay: -0.32s;
    }
    &:nth-child(2) {
      animation-delay: -0.16s;
    }
    &:nth-child(3) {
      animation-delay: 0s;
    }
  }

  .typing-text {
    margin-left: 8px;
    color: #999;
    font-size: 13px;
  }
}

// Markdown 样式
.markdown-body {
  line-height: 1.6;

  :deep(h1),
  :deep(h2),
  :deep(h3),
  :deep(h4) {
    margin: 0.5em 0;
    font-weight: 600;
  }

  :deep(p) {
    margin: 0.5em 0;
  }

  :deep(ul),
  :deep(ol) {
    padding-left: 2em;
    margin: 0.5em 0;
    list-style-position: outside;
  }

  // 恢复列表项的编号/项目符号（reset.scss 中全局重置了 list-style: none）
  :deep(ol li) {
    list-style-type: decimal;
  }

  :deep(ul li) {
    list-style-type: disc;
  }

  :deep(code) {
    background: rgba(0, 0, 0, 0.06);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: monospace;
  }

  :deep(pre) {
    background: #f6f8fa;
    padding: 12px;
    border-radius: 6px;
    overflow-x: auto;

    code {
      background: transparent;
      padding: 0;
    }
  }

  :deep(table) {
    border-collapse: collapse;
    width: 100%;
    margin: 0.5em 0;

    th,
    td {
      border: 1px solid #ddd;
      padding: 6px 12px;
      text-align: left;
    }

    th {
      background: #f6f8fa;
    }
  }

  :deep(blockquote) {
    border-left: 4px solid var(--el-color-primary);
    padding-left: 12px;
    margin: 0.5em 0;
    color: #666;
  }
}

// 消息内容包装器（用于光标定位）
.message-content-wrapper {
  display: inline;
}

// 打字机光标样式
.typewriter-cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  background-color: var(--el-color-primary);
  margin-left: 2px;
  vertical-align: text-bottom;
  transition: opacity 0.1s;

  &.hidden {
    opacity: 0;
  }
}

// 历史侧边栏
.history-sidebar {
  width: 280px;
  border-left: 1px solid #f0f0f0;
  background: #fafbfc;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;

  .history-sidebar-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    border-bottom: 1px solid #f0f0f0;
    flex-shrink: 0;

    .history-title {
      font-weight: 500;
      font-size: 14px;
    }
  }

  .history-list {
    flex: 1;
    overflow-y: auto;

    .history-item {
      display: flex;
      align-items: center;
      padding: 12px 16px;
      border-bottom: 1px solid #f0f0f0;
      cursor: pointer;
      transition: background 0.2s;

      &:hover {
        background: #f0f0f0;
      }

      &.active {
        background: var(--el-color-primary-light-9);
      }

      .history-info {
        flex: 1;
        min-width: 0;

        .history-preview {
          font-size: 13px;
          color: #333;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .history-meta {
          font-size: 12px;
          color: #999;
          margin-top: 4px;
        }
      }
    }
  }
}

// 快捷指令
.quick-commands {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  border-top: 1px solid #f0f0f0;
  flex-wrap: wrap;
  flex-shrink: 0;
}

// 输入区域
.input-area {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  background: #fafbfc;
  border-top: 1px solid #f0f0f0;
  flex-shrink: 0;

  .input-wrapper {
    flex: 1;
    position: relative;

    .input-actions {
      position: absolute;
      right: 8px;
      bottom: 8px;
      display: flex;
      align-items: center;
      gap: 4px;

      .voice-temp-result {
        font-size: 12px;
        color: #999;
        padding-right: 8px;
        border-right: 1px solid #e8e8e8;
        margin-right: 8px;
        max-width: 200px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .voice-recording {
        color: var(--el-color-danger);
        animation: pulse 1.5s infinite;
      }
    }
  }
}

// 设备状态抽屉内容
.device-status-content {
  .device-action-section {
    margin: 20px 0;
    text-align: center;
  }

  .tag-points-section {
    h4 {
      margin: 16px 0 12px;
      font-size: 14px;
      color: #333;
    }
  }
}

// 动画
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes bounce {
  0%,
  80%,
  100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

@keyframes pulse {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
  100% {
    opacity: 1;
  }
}

// 过渡动画
.slide-fade-enter-active {
  transition: all 0.3s ease;
}

.slide-fade-leave-active {
  transition: all 0.2s ease;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateX(20px);
  opacity: 0;
}
</style>
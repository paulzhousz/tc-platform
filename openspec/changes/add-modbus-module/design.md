# Modbus 控制模块设计文档

## 1. 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Frontend Layer                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐ │
│  │   Device Tree   │  │   Chat Panel    │  │   Device Detail Drawer      │ │
│  │   (Element Plus)│  │   (Element Plus)│  │   (Element Plus)            │ │
│  └────────┬────────┘  └────────┬────────┘  └─────────────┬───────────────┘ │
│           │                    │                         │                  │
│  ┌────────▼────────────────────▼─────────────────────────▼───────────────┐ │
│  │                        Pinia Store (modbus)                            │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
                  │                              │
        ┌─────────┴─────────┐          ┌─────────▼─────────┐
        │    REST API       │          │    WebSocket      │
        └─────────┬─────────┘          └─────────┬─────────┘
                  │                              │
┌─────────────────┴───────────────────────────────────────────────────────────┐
│                              Backend Layer                                   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                    plugin/module_modbus/                                 ││
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐           ││
│  │  │  device/   │ │  control/  │ │    log/    │ │  pending/  │           ││
│  │  │  routers   │ │  routers   │ │  routers   │ │  routers   │           ││
│  │  └──────┬─────┘ └──────┬─────┘ └────────────┘ └────────────┘           ││
│  │         │              │                                                ││
│  │  ┌──────▼──────────────▼──────────────────────────────────────────────┐ ││
│  │  │                       Services Layer                                │ ││
│  │  │  ┌─────────────┐ ┌─────────────┐ ┌───────────────────────────────┐ │ ││
│  │  │  │ PLCService  │ │AgentService │ │ ConnectionPool                │ │ ││
│  │  │  │ - read()    │ │ - chat()    │ │ - acquire() / release()       │ │ ││
│  │  │  │ - write()   │ │ - stream()  │ │ - health_check()              │ │ ││
│  │  │  │ - adjust()  │ │ - Tools     │ │ - add_device() / remove()     │ │ ││
│  │  │  └─────────────┘ └─────────────┘ └───────────────────────────────┘ │ ││
│  │  └─────────────────────────────────────────────────────────────────────┘ ││
│  │                                                                          ││
│  │  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  │                          models.py                                   ││
│  │  │  Device | TagPoint | CommandLog | PendingConfirm | AgentSession     ││
│  │  │  ChatHistory | ActionStep                                          ││
│  │  └─────────────────────────────────────────────────────────────────────┘││
│  └──────────────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                              ┌────────▼────────┐
                              │  PLC Devices    │
                              │  (Modbus TCP)   │
                              └─────────────────┘
```

## 2. 数据模型设计

### 2.1 Device（设备）

> **设计说明**：PLC 设备是**共享工业资源**，所有用户应能看到和控制同一批设备，因此不继承 `UserMixin`。操作审计通过 `CommandLogModel.user_id` 记录具体操作人。

```python
class DeviceModel(ModelMixin):
    """PLC 设备"""
    __tablename__ = "modbus_devices"

    # 基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="设备名称")
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="设备编码")
    description: Mapped[str | None] = mapped_column(Text, comment="描述")
    group_name: Mapped[str | None] = mapped_column(String(50), comment="分组名称")

    # 连接配置
    connection_type: Mapped[str] = mapped_column(String(20), default="TCP", comment="连接类型")
    host: Mapped[str] = mapped_column(String(100), nullable=False, comment="IP地址")
    port: Mapped[int] = mapped_column(Integer, default=502, comment="端口")
    slave_id: Mapped[int] = mapped_column(Integer, default=1, comment="从站ID")
    baud_rate: Mapped[int | None] = mapped_column(Integer, default=9600, comment="波特率")
    parity: Mapped[str | None] = mapped_column(String(10), default="N", comment="校验位")

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    status: Mapped[str] = mapped_column(String(20), default="offline", comment="状态")
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, comment="最后在线时间")

    # 关系
    tags: Mapped[list["TagPointModel"]] = relationship(
        "TagPointModel", back_populates="device", cascade="all, delete-orphan"
    )
```

### 2.2 TagPoint（点位）

```python
class TagPointModel(ModelMixin):
    """设备点位"""
    __tablename__ = "modbus_tags"

    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("modbus_devices.id", ondelete="CASCADE"), nullable=False
    )

    # 基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="点位名称")
    code: Mapped[str] = mapped_column(String(50), nullable=False, comment="点位编码")
    description: Mapped[str | None] = mapped_column(Text, comment="描述")

    # Modbus 地址
    address: Mapped[int] = mapped_column(Integer, nullable=False, comment="寄存器地址")
    register_type: Mapped[str] = mapped_column(String(20), default="holding", comment="寄存器类型")
    data_type: Mapped[str] = mapped_column(String(20), default="INT16", comment="数据类型")
    byte_order: Mapped[str] = mapped_column(String(10), default="big", comment="字节序")

    # 访问控制
    access_type: Mapped[str] = mapped_column(String(20), default="READ_WRITE", comment="访问类型")

    # 数值范围
    min_value: Mapped[float] = mapped_column(Float, default=0, comment="最小值")
    max_value: Mapped[float] = mapped_column(Float, default=100, comment="最大值")
    unit: Mapped[str | None] = mapped_column(String(20), comment="单位")
    scale_factor: Mapped[float] = mapped_column(Float, default=1.0, comment="缩放因子")
    offset: Mapped[float] = mapped_column(Float, default=0.0, comment="偏移量")

    # AI 语义匹配
    aliases: Mapped[list | None] = mapped_column(JSON, comment="语义别名")

    # 安全策略
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, default=False, comment="需要确认")
    confirmation_threshold: Mapped[float | None] = mapped_column(Float, comment="确认阈值")

    # 缓存
    current_value: Mapped[float | None] = mapped_column(Float, comment="当前值")
    last_updated: Mapped[datetime | None] = mapped_column(DateTime, comment="最后更新时间")

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序")

    # 关系
    device: Mapped["DeviceModel"] = relationship("DeviceModel", back_populates="tags")
```

### 2.3 CommandLog（PLC 操作日志）

> **重要说明**：`CommandLogModel` 用于记录 PLC 控制操作的业务审计日志，与系统的 `OperationLogRoute`（HTTP 请求审计）是独立的两个日志体系。
> - `OperationLogRoute`：记录所有 HTTP API 请求的用户操作审计
> - `CommandLogModel`：记录 PLC 设备的读写操作详情，包含设备ID、点位ID、操作值、执行状态等

```python
class CommandLogModel(ModelMixin):
    """PLC 操作审计日志"""
    __tablename__ = "modbus_command_logs"

    # 操作来源
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(50), comment="Agent 会话ID")

    # 操作目标
    device_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("modbus_devices.id"))
    tag_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("modbus_tags.id"))

    # 操作内容
    action: Mapped[str] = mapped_column(String(10), nullable=False, comment="READ/WRITE")
    request_value: Mapped[float | None] = mapped_column(Float, comment="请求值")
    actual_value: Mapped[float | None] = mapped_column(Float, comment="实际值")

    # 结果
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="pending/success/failed/cancelled")
    error_message: Mapped[str | None] = mapped_column(Text, comment="错误信息")

    # 确认信息
    confirmation_required: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否需要确认")
    confirmed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)

    # AI 信息
    ai_reasoning: Mapped[str | None] = mapped_column(Text, comment="AI 推理过程")
    user_input: Mapped[str | None] = mapped_column(Text, comment="用户原始输入")

    # 执行详情
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    execution_time: Mapped[float | None] = mapped_column(Float, comment="执行耗时(ms)")
    executed_at: Mapped[datetime | None] = mapped_column(DateTime)
```

### 2.4 PendingConfirm（待确认操作）

```python
class PendingConfirmModel(ModelMixin):
    """待人工确认的操作"""
    __tablename__ = "modbus_pending_confirms"

    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    command_log_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("modbus_command_logs.id"))

    # 操作详情（冗余存储，便于展示）
    device_name: Mapped[str | None] = mapped_column(String(100))
    tag_name: Mapped[str | None] = mapped_column(String(100))
    target_value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(20))

    # 状态
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="pending/confirmed/rejected/expired")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, comment="过期时间")

    # 审核信息
    reviewed_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    review_comment: Mapped[str | None] = mapped_column(Text)

    # AI 信息
    user_input: Mapped[str | None] = mapped_column(Text)
    ai_explanation: Mapped[str | None] = mapped_column(Text)
```

### 2.5 AgentSession（LLM Agent 会话）

```python
class AgentSessionModel(ModelMixin):
    """LLM Agent 会话"""
    __tablename__ = "modbus_agent_sessions"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    session_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # 上下文（简单字段，向后兼容）
    last_device_id: Mapped[int | None] = mapped_column(Integer)
    last_tag_id: Mapped[int | None] = mapped_column(Integer)

    # 详细操作上下文
    # 结构: {"last_device": {...}, "last_tag": {...}, "last_operation": {...}}
    operation_context: Mapped[dict | None] = mapped_column(JSON)

    # 对话历史
    chat_history: Mapped[list | None] = mapped_column(JSON)

    # 时间
    last_active: Mapped[datetime | None] = mapped_column(DateTime)
    ttl_minutes: Mapped[int] = mapped_column(Integer, default=10)
```

### 2.6 ChatHistory（聊天历史）

```python
class ChatHistoryModel(ModelMixin):
    """用户聊天历史（长期存储）"""
    __tablename__ = "modbus_chat_history"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    # 预览信息
    title: Mapped[str | None] = mapped_column(String(200), comment="首条用户消息摘要")

    # 对话内容
    messages: Mapped[list] = mapped_column(JSON, nullable=False)

    # 设备上下文
    device_count: Mapped[int] = mapped_column(Integer, default=0)
    device_names: Mapped[list | None] = mapped_column(JSON)

    # 时间
    start_time: Mapped[datetime | None] = mapped_column(DateTime)
    end_time: Mapped[datetime | None] = mapped_column(DateTime)

## 3. 配置项设计

### 3.1 环境变量配置

```bash
# ========== Modbus 控制模块配置 ==========

# LLM Agent 配置
MODBUS_LLM_BASE_URL=https://api-inference.modelscope.cn/v1/
MODBUS_LLM_API_KEY=your-api-key
MODBUS_LLM_MODEL_NAME=Qwen/Qwen3-8B
MODBUS_LLM_TEMPERATURE=0
MODBUS_LLM_SESSION_TTL_MINUTES=10
MODBUS_LLM_MAX_HISTORY_TURNS=20

# Modbus 连接池配置
MODBUS_POOL_SIZE=5
MODBUS_CONNECT_TIMEOUT=5
MODBUS_READ_TIMEOUT=3
MODBUS_IDLE_TIMEOUT=300

# 重试配置
MODBUS_RETRY_ENABLED=true
MODBUS_RETRY_TIMES=3
MODBUS_RETRY_INTERVAL=1.0

# 状态轮询配置
MODBUS_POLL_ENABLED=true
MODBUS_POLL_INTERVAL=5

# 日志保留配置
MODBUS_LOG_RETENTION_DAYS=90
MODBUS_PENDING_EXPIRE_MINUTES=10

# FunASR 语音服务配置（现有基础设施，直接连接使用）
MODBUS_FUNASR_WS_URL=ws://localhost:10095
MODBUS_FUNASR_MODE=2pass-offline
MODBUS_FUNASR_AUDIO_FS=16000
MODBUS_SILENCE_THRESHOLD=0.01
MODBUS_SILENCE_DURATION=5
```

> **注意**：FunASR WebSocket 服务是现有基础设施，已在 `ws://localhost:10095` 运行，前端直接连接使用即可，无需在本模块中部署或实现。
```

### 3.2 配置类定义

```python
# backend/app/config/setting.py 中添加

class Settings:
    # ... 现有配置 ...

    # ========== Modbus 控制模块配置 ==========
    # LLM Agent 配置
    MODBUS_LLM_BASE_URL: str = "https://api-inference.modelscope.cn/v1/"
    MODBUS_LLM_API_KEY: str = ""
    MODBUS_LLM_MODEL_NAME: str = "Qwen/Qwen3-8B"
    MODBUS_LLM_TEMPERATURE: float = 0
    MODBUS_LLM_SESSION_TTL_MINUTES: int = 10
    MODBUS_LLM_MAX_HISTORY_TURNS: int = 20

    # Modbus 连接池配置
    MODBUS_POOL_SIZE: int = 5
    MODBUS_CONNECT_TIMEOUT: int = 5
    MODBUS_READ_TIMEOUT: int = 3
    MODBUS_IDLE_TIMEOUT: int = 300

    # 重试配置
    MODBUS_RETRY_ENABLED: bool = True
    MODBUS_RETRY_TIMES: int = 3
    MODBUS_RETRY_INTERVAL: float = 1.0

    # 状态轮询配置
    MODBUS_POLL_ENABLED: bool = True
    MODBUS_POLL_INTERVAL: int = 5

    # 日志保留配置
    MODBUS_LOG_RETENTION_DAYS: int = 90
    MODBUS_PENDING_EXPIRE_MINUTES: int = 10

    # FunASR 语音服务配置（现有基础设施，直接连接使用）
    MODBUS_FUNASR_WS_URL: str = "ws://localhost:10095"
    MODBUS_FUNASR_MODE: str = "2pass-offline"
    MODBUS_FUNASR_AUDIO_FS: int = 16000
    MODBUS_SILENCE_THRESHOLD: float = 0.01
    MODBUS_SILENCE_DURATION: float = 5
```

## 4. 前端组件映射

### 4.1 组件对照表

| 源项目 (Ant Design Vue) | 目标项目 (Element Plus) | 迁移说明 |
|------------------------|------------------------|---------|
| `a-layout`, `a-layout-sider` | `el-container`, `el-aside` | 结构类似 |
| `a-tree` | `el-tree` | `treeData` → `data`, `onSelect` → `@node-click` |
| `a-card` | `el-card` | 基本兼容 |
| `a-button` | `el-button` | `type="primary"` 兼容 |
| `a-input`, `a-textarea` | `el-input` | `a-textarea` 使用 `type="textarea"` |
| `a-select` | `el-select` | `options` 结构不同 |
| `a-table` | `el-table` | 列定义方式不同 |
| `a-modal` | `el-dialog` | `v-model:open` → `v-model` |
| `a-drawer` | `el-drawer` | 基本兼容 |
| `a-form`, `a-form-item` | `el-form`, `el-form-item` | 验证规则格式不同 |
| `a-tag` | `el-tag` | `color` → `type` |
| `a-tooltip` | `el-tooltip` | 基本兼容 |
| `a-spin` | `v-loading` 指令 | 使用方式不同 |
| `a-empty` | `el-empty` | 基本兼容 |
| `a-message.success()` | `ElMessage.success()` | 函数调用方式相同 |
| `a-popconfirm` | `el-popconfirm` | 基本兼容，气泡确认框 |
| `a-descriptions` | `el-descriptions` | 描述列表，基本兼容 |
| `a-badge` | `el-badge` | 徽标，基本兼容 |
| `a-dropdown` | `el-dropdown` | 下拉菜单，基本兼容 |
| `a-switch` | `el-switch` | 开关，基本兼容 |
| `a-radio-group` | `el-radio-group` | 单选组，基本兼容 |
| `a-checkbox-group` | `el-checkbox-group` | 多选组，基本兼容 |

### 4.2 样式适配

- 使用 UnoCSS 原子类，保持一致
- 主题变量使用 Element Plus CSS 变量

## 5. 关键服务设计

### 5.1 ConnectionPool（连接池）

```python
class ModbusConnectionPool:
    """Modbus 连接池管理"""

    def __init__(self):
        self._pools: Dict[int, Queue] = {}  # device_id -> connection queue
        self._device_configs: Dict[int, DeviceModel] = {}
        self._lock = threading.Lock()

    def add_device(self, device: DeviceModel) -> bool:
        """添加设备，创建连接池"""

    def remove_device(self, device_id: int):
        """移除设备，关闭所有连接"""

    def acquire(self, device_id: int, timeout: float = 10) -> IModbusClient | None:
        """获取连接（阻塞）"""

    def release(self, device_id: int, client: IModbusClient):
        """释放连接回池"""

    def health_check(self, device_id: int) -> dict:
        """健康检查"""
```

### 5.2 AgentService（LLM Agent）

```python
class AgentService:
    """LLM Agent 服务"""

    TOOLS = [
        search_device,       # 搜索设备
        search_tag_mapping,  # 搜索点位
        read_plc,            # 读取 PLC
        write_plc,           # 写入 PLC
        adjust_plc,          # 调整参数
        confirm_operation,   # 确认操作
        cancel_operation,    # 取消操作
    ]

    def chat(self, user_id: int, message: str, session_id: str | None) -> dict:
        """同步对话"""

    async def stream_chat(self, user_id: int, message: str, session_id: str | None):
        """流式对话，通过 SSE 返回"""
```

### 5.3 PLCService（PLC 操作）

```python
class PLCService:
    """PLC 操作服务"""

    def read(self, device_id: int, tag_code: str, user_id: int | None = None) -> dict:
        """读取点位值"""

    def write(self, device_id: int, tag_code: str, value: float, ...) -> dict:
        """写入点位值"""

    def adjust(self, device_id: int, tag_code: str, delta: float, ...) -> dict:
        """调整参数增量"""

    def search_devices(self, keyword: str) -> dict:
        """搜索设备（AI 用）"""

    def search_tags_in_device(self, device_id: int, query: str) -> dict:
        """在设备下搜索点位（AI 用）"""
```

## 6. 前端页面结构

### 6.1 控制页面 (control/index.vue)

```
┌─────────────────────────────────────────────────────────────────┐
│  [连接按钮] [断开按钮]                    [历史按钮] [设置按钮]  │
├───────────────────┬─────────────────────────────────────────────┤
│                   │                                             │
│   设备树          │              聊天面板                        │
│   ┌───────────┐   │   ┌─────────────────────────────────────┐   │
│   │ 分组1     │   │   │ 用户: 空调温度是多少                 │   │
│   │  ├ 设备1  │   │   │ AI: 智能空调当前温度为 26°C          │   │
│   │  └ 设备2  │   │   │ 用户: 把温度调高2度                  │   │
│   │ 分组2     │   │   │ AI: 已将温度从 26°C 调整为 28°C      │   │
│   │  └ 设备3  │   │   └─────────────────────────────────────┘   │
│   └───────────┘   │                                             │
│                   │   ┌─────────────────────────────────────┐   │
│                   │   │ [快捷指令1] [快捷指令2] [快捷指令3]   │   │
│                   │   └─────────────────────────────────────┘   │
│                   │                                             │
│                   │   ┌─────────────────────────────────────┐   │
│                   │   │ [🎤] 输入消息...              [发送] │   │
│                   │   └─────────────────────────────────────┘   │
└───────────────────┴─────────────────────────────────────────────┘
```

### 6.2 设备管理页面 (device/index.vue)

- 表格展示设备列表
- 支持 CRUD 操作
- 点位管理通过抽屉或弹窗

## 7. 安全控制机制

### 7.1 写入操作确认

所有 write/adjust 操作必须经过以下安全检查：

| 检查项 | 触发条件 | 处理方式 |
|-------|---------|---------|
| 强制确认 | `TagPointModel.requires_confirmation == True` | 必须用户确认 |
| 范围校验 | `value < min_value` 或 `value > max_value` | 直接拒绝，返回错误 |
| 阈值确认 | `value` 超过 `confirmation_threshold` 比例 | 必须用户确认 |
| 只读保护 | `TagPointModel.access_type == 'READ'` | 直接拒绝写入 |

### 7.2 待确认操作超时

```python
# PendingConfirmModel 在创建时设置过期时间
expires_at = datetime.now() + timedelta(minutes=settings.MODBUS_PENDING_EXPIRE_MINUTES)

# 过期后操作视为已拒绝，CleanupService 定期清理
```

### 7.3 权限校验

| 操作 | 所需权限 |
|-----|---------|
| 读取 PLC | `modbus:control:read` |
| 写入 PLC | `modbus:control:write` |
| 确认操作 | `modbus:pending:confirm` |

### 7.4 LLM Agent 安全措施

1. **工具沙箱**：LLM 只能调用预定义的工具，不能执行任意代码
2. **参数校验**：所有工具参数经过 Pydantic 验证
3. **操作审计**：所有 PLC 操作记录到 `CommandLogModel`
4. **人工确认**：高风险操作必须人工确认后才执行

## 8. WebSocket 消息协议

### 8.1 连接认证

```javascript
// 客户端连接时携带 token
const ws = new WebSocket(`ws://host/ws/modbus?token=${jwtToken}`);
```

### 8.2 服务端推送消息格式

```typescript
// 设备状态变化
{
  "type": "device_status",
  "data": {
    "device_id": 1,
    "device_name": "智能空调",
    "status": "online",
    "last_seen": "2026-03-24T21:00:00Z"
  }
}

// 点位值变化
{
  "type": "tag_value",
  "data": {
    "device_id": 1,
    "tag_id": 5,
    "tag_name": "温度设定值",
    "value": 26.0,
    "unit": "°C",
    "previous_value": 25.0
  }
}

// 操作结果通知
{
  "type": "operation_result",
  "data": {
    "command_log_id": 123,
    "success": true,
    "message": "写入成功"
  }
}

// 待确认操作通知
{
  "type": "pending_confirm",
  "data": {
    "pending_confirm_id": 1,
    "device_name": "智能空调",
    "tag_name": "频率设定",
    "target_value": 50,
    "unit": "Hz"
  }
}
```

## 9. 数据库迁移

### 9.1 Alembic 迁移脚本

```python
# alembic/versions/xxx_add_modbus_tables.py

def upgrade():
    # 创建 modbus_devices 表
    op.create_table(
        'modbus_devices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        # ... 其他字段
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # 创建 modbus_tags 表
    # 创建 modbus_command_logs 表
    # 创建 modbus_pending_confirms 表
    # 创建 modbus_agent_sessions 表
    # 创建 modbus_chat_history 表

def downgrade():
    op.drop_table('modbus_chat_history')
    op.drop_table('modbus_agent_sessions')
    op.drop_table('modbus_pending_confirms')
    op.drop_table('modbus_command_logs')
    op.drop_table('modbus_tags')
    op.drop_table('modbus_devices')
```
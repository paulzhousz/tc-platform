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

```python
class DeviceModel(ModelMixin, UserMixin):
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

### 2.3 其他模型

- **CommandLogModel**: 操作审计日志
- **PendingConfirmModel**: 待确认操作
- **AgentSessionModel**: LLM Agent 会话
- **ChatHistoryModel**: 聊天历史

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

# FunASR 语音服务配置
MODBUS_FUNASR_WS_URL=ws://localhost:10095
MODBUS_FUNASR_MODE=2pass-offline
MODBUS_FUNASR_AUDIO_FS=16000
MODBUS_SILENCE_THRESHOLD=0.01
MODBUS_SILENCE_DURATION=5
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

    # FunASR 语音服务配置
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

## 7. 数据库迁移

### 7.1 Alembic 迁移脚本

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
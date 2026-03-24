# Modbus 设备控制模块设计文档

**版本**: 1.0
**创建日期**: 2026-03-22
**最后更新**: 2026-03-22

---

## 1. 系统概述

### 1.1 设计目标

设备控制模块采用**分层架构**设计，实现业务逻辑与技术实现的解耦，支持：

1. **协议无关性**: 通过抽象接口支持多种 Modbus 连接方式
2. **高可用性**: 连接池管理、自动重连、健康检查
3. **智能化控制**: LLM Agent 驱动的自然语言交互
4. **多模态输入**: 支持文本和语音两种输入方式
5. **可扩展性**: 工具化设计，易于扩展新的操作类型

### 1.2 技术栈

| 层级 | 技术选型 |
|------|----------|
| 后端框架 | FastAPI + SQLAlchemy |
| Modbus 通信 | pymodbus |
| LLM 集成 | LangChain + OpenAI API |
| 语音识别 | FunASR (Docker 服务) |
| 前端框架 | Vue 3 + TypeScript + Ant Design Vue |
| 状态管理 | Pinia |
| 实时通信 | WebSocket + SSE |
| 数据库 | SQLite / PostgreSQL |

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Frontend Layer                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐ │
│  │   Device Tree   │  │   Chat Panel    │  │   Device Detail Drawer      │ │
│  │   Component     │  │   Component     │  │   Component                 │ │
│  └────────┬────────┘  └────────┬────────┘  └─────────────┬───────────────┘ │
│           │                    │                         │                  │
│  ┌────────▼────────────────────▼─────────────────────────▼───────────────┐ │
│  │                        Pinia Store (modbus)                            │ │
│  │  - devices, tagPoints, messages, sessionId, chatHistory               │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    Voice Input Layer (Composables)                     │ │
│  │  ┌─────────────────────────┐  ┌─────────────────────────────────────┐  │ │
│  │  │   useFunASRWs           │  │   AudioWorklet Processor            │  │ │
│  │  │   - WebSocket 连接      │  │   - 16kHz 重采样                    │  │ │
│  │  │   - 识别结果处理        │  │   - 静音检测                        │  │ │
│  │  └───────────┬─────────────┘  │   - PCM 编码                        │  │ │
│  │              │                └─────────────────────────────────────┘  │ │
│  └──────────────┼─────────────────────────────────────────────────────────┘ │
└─────────────────┼───────────────────────────────────────────────────────────┘
                  │                              │
        ┌─────────┴─────────┐          ┌─────────▼─────────┐
        │                   │          │                   │
  ┌─────▼─────┐       ┌─────▼─────┐    │   FunASR Docker   │
  │  REST API │       │  WebSocket │    │   ws://:10095    │
  └─────┬─────┘       └─────┬─────┘    │   语音识别服务    │
        │                   │          └───────────────────┘
        │                   │
┌───────┴───────────────────┴───────────────────────────────────────────────┐
│                              Backend Layer                                  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                         Routers Layer                                  │ │
│  │  ┌────────────────┐ ┌────────────────┐                                │ │
│  │  │  device.py     │ │  control.py    │                                │ │
│  │  │  /devices/*    │ │  /control/*    │                                │ │
│  │  └───────┬────────┘ └───────┬────────┘                                │ │
│  └──────────┼──────────────────┼──────────────────────────────────────────┘ │
│             │                  │                                            │
│  ┌──────────▼──────────────────▼──────────────────────────────────────────┐ │
│  │                        Services Layer                                   │ │
│  │                                                                         │ │
│  │  ┌─────────────────┐ ┌─────────────────┐ ┌───────────────────────────┐ │ │
│  │  │   PLCService    │ │  AgentService   │ │  CleanupService           │ │ │
│  │  │  - read()       │ │  - chat()       │ │  - cleanup_command_logs() │ │ │
│  │  │  - write()      │ │  - stream_chat()│ │  - cleanup_agent_sessions│ │ │
│  │  │  - adjust()     │ │  - Tools        │ │  - cleanup_pending()      │ │ │
│  │  │  - search_*()   │ │                 │ │                           │ │ │
│  │  └────────┬────────┘ └────────┬────────┘ └───────────────────────────┘ │ │
│  │           │                   │                                         │ │
│  │  ┌────────▼───────────────────▼────────────────────────────────────────┐│ │
│  │  │              ConnectionPool (connection_pool.py)                     ││ │
│  │  │              - acquire() / release() / health_check()               ││ │
│  │  └───────────────────────────┬─────────────────────────────────────────┘│ │
│  │                              │                                           │ │
│  │  ┌───────────────────────────▼─────────────────────────────────────────┐│ │
│  │  │              ClientFactory (client_factory.py)                       ││ │
│  │  │              - TcpModbusClient / RtuOverTcpClient                   ││ │
│  │  └─────────────────────────────────────────────────────────────────────┘│ │
│  └──────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────────┐│
│  │                         Data Layer                                       ││
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐            ││
│  │  │   Device   │ │  TagPoint  │ │ AgentSession│ │ ChatHistory│            ││
│  │  │            │ │            │ │            │ │            │            ││
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘            ││
│  └──────────────────────────────────────────────────────────────────────────┘│
└───────────────────────────────────────────────────────────────────────────────┘
                                       │
                              ┌────────▼────────┐
                              │  PLC Devices    │
                              │  (Modbus TCP)   │
                              └─────────────────┘
```

### 2.2 模块职责划分

| 模块 | 文件 | 职责 |
|------|------|------|
| **Routers** | `routers/device.py` | 设备/点位 CRUD API |
| | `routers/control.py` | 控制操作 API（连接、对话、读写） |
| **Services** | `services/plc_service.py` | PLC 读写业务逻辑 |
| | `services/agent_service.py` | LLM Agent 集成 |
| | `services/connection_pool.py` | 连接池管理 |
| | `services/client_factory.py` | Modbus 客户端工厂 |
| | `services/cleanup_service.py` | 数据清理服务 |
| **Models** | `models.py` | 数据模型定义 |
| **Schemas** | `schemas.py` | Pydantic 验证模型 |

---

## 3. 核心数据模型

### 3.1 ER 图

```
┌───────────────────┐       ┌───────────────────┐
│      Device       │       │     TagPoint      │
├───────────────────┤       ├───────────────────┤
│ id (PK)           │───┐   │ id (PK)           │
│ name              │   │   │ device_id (FK)    │◄──┐
│ code (UK)         │   │   │ name              │   │
│ description       │   │   │ code              │   │
│ group_name        │   │   │ address           │   │
│ connection_type   │   │   │ register_type     │   │
│ host              │   │   │ data_type         │   │
│ port              │   │   │ access_type       │   │
│ slave_id          │   │   │ min_value         │   │
│ status            │   │   │ max_value         │   │
│ is_active         │   │   │ unit              │   │
│ last_seen         │   │   │ scale_factor      │   │
└───────────────────┘   │   │ offset            │   │
                        │   │ aliases (JSON)    │   │
                        │   │ requires_confirm  │   │
                        │   │ current_value     │   │
                        │   └───────────────────┘   │
                        │                           │
                        └───────────────────────────┘

┌───────────────────┐       ┌───────────────────┐
│   AgentSession    │       │    ChatHistory    │
├───────────────────┤       ├───────────────────┤
│ id (PK)           │       │ id (PK)           │
│ user_id (FK)      │       │ user_id (FK)      │
│ session_id (UK)   │       │ session_id (UK)   │
│ last_device_id    │       │ title             │
│ last_tag_id       │       │ messages (JSON)   │
│ operation_context │       │ device_count      │
│ chat_history (JSON│       │ device_names(JSON)│
│ ttl_minutes       │       │ start_time        │
│ last_active       │       │ end_time          │
└───────────────────┘       └───────────────────┘
```

### 3.2 模型详细定义

#### Device（设备）

```python
class Device(Base):
    __tablename__ = "modbus_devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)          # 设备名称
    code = Column(String(50), unique=True, nullable=False)  # 设备编码（唯一）
    description = Column(Text)                          # 描述
    group_name = Column(String(50))                     # 分组名称

    # 连接配置
    connection_type = Column(String(20), default="TCP") # TCP | RTU_OVER_TCP
    host = Column(String(100), nullable=False)          # IP 地址
    port = Column(Integer, default=502)                 # 端口
    slave_id = Column(Integer, default=1)               # 从站ID

    # RTU 参数
    baud_rate = Column(Integer, default=9600)           # 波特率
    parity = Column(String(10), default="N")            # 校验位

    # 状态
    is_active = Column(Boolean, default=True)           # 是否启用
    status = Column(String(20), default="offline")      # online | offline | error
    last_seen = Column(DateTime)                        # 最后在线时间
```

#### TagPoint（点位）

```python
class TagPoint(Base):
    __tablename__ = "modbus_tags"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("modbus_devices.id", ondelete="CASCADE"))

    name = Column(String(100), nullable=False)          # 点位名称
    code = Column(String(50), nullable=False)           # 点位编码
    description = Column(Text)

    # Modbus 地址
    address = Column(Integer, nullable=False)           # 寄存器地址
    register_type = Column(String(20), default="holding")  # holding|input|coil|discrete

    # 数据类型
    data_type = Column(String(20), default="INT16")     # INT16|UINT16|INT32|FLOAT|BOOL
    byte_order = Column(String(10), default="big")      # big | little

    # 访问控制
    access_type = Column(String(20), default="READ_WRITE")  # READ|WRITE|READ_WRITE

    # 数值范围与转换
    min_value = Column(Float, default=0)
    max_value = Column(Float, default=100)
    unit = Column(String(20))
    scale_factor = Column(Float, default=1.0)           # 工程值 = 原始值 × scale + offset
    offset = Column(Float, default=0.0)

    # AI 语义匹配
    aliases = Column(JSON, default=list)                # ["温度", "主温度"]

    # 安全策略
    requires_confirmation = Column(Boolean, default=False)
    confirmation_threshold = Column(Float)              # 0.8 = 超过80%范围需确认

    # 缓存
    current_value = Column(Float)                       # 当前值
    last_updated = Column(DateTime)                     # 最后更新时间
```

#### AgentSession（Agent 会话）

```python
class AgentSession(Base):
    __tablename__ = "modbus_agent_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(String(50), unique=True)        # 会话唯一标识

    # 上下文（简单字段，向后兼容）
    last_device_id = Column(Integer)
    last_tag_id = Column(Integer)

    # 详细操作上下文
    operation_context = Column(JSON, default=dict)
    # 结构示例:
    # {
    #     "last_device": {"id": 2, "name": "智能空调", "matched_keyword": "空调"},
    #     "last_tag": {"id": 5, "name": "设定温度", "device_id": 2},
    #     "last_operation": {"type": "write", "value": 30}
    # }

    chat_history = Column(JSON, default=list)           # 对话历史
    ttl_minutes = Column(Integer, default=10)           # 会话TTL
    last_active = Column(DateTime)                      # 最后活跃时间
```

---

## 4. 核心服务设计

### 4.1 PLCService（PLC 操作服务）

**职责**: 协议无关的 PLC 读写业务逻辑

```python
class PLCService:
    def __init__(self, db: Session):
        self.db = db

    def read(self, device_id: int, tag_code: str, user_id: int = None) -> Dict:
        """
        读取点位值
        1. 获取点位元数据
        2. 记录操作日志（pending）
        3. 获取连接
        4. 读取寄存器
        5. 数值转换（原始值 → 工程值）
        6. 更新缓存和日志
        7. 返回结构化数据
        """

    def write(self, device_id: int, tag_code: str, value: float, ...) -> Dict:
        """
        写入点位值
        1. 获取点位元数据
        2. 权限检查（是否只读）
        3. 范围校验
        4. 检查是否需要人工确认
        5. 执行写入
        6. 返回结果
        """

    def adjust(self, device_id: int, tag_code: str, delta: float, ...) -> Dict:
        """
        调整参数增量
        1. 读取当前值
        2. 计算新值 = 当前值 + delta
        3. 写入新值
        4. 返回调整结果（含前后值）
        """

    def search_devices(self, keyword: str) -> Dict:
        """搜索设备（用于 AI 匹配）"""

    def search_tags_in_device(self, device_id: int, query: str) -> Dict:
        """在指定设备下搜索点位"""
```

#### 地址转换逻辑

```python
def _normalize_address(self, address: int, register_type: str) -> int:
    """
    PLC 编程地址 → Modbus 协议地址

    保持寄存器: 40001-49999 → 0-9999
    输入寄存器: 30001-39999 → 0-9999
    线圈:       1-9999     → 0-9998
    离散输入:   1-9999     → 0-9998
    """
    if register_type == "holding" and address >= 40001:
        return address - 40001
    elif register_type == "input" and address >= 30001:
        return address - 30001
    elif register_type in ["coil", "discrete"] and address >= 1:
        return address - 1
    return address
```

#### 数值转换逻辑

```python
# 原始值 → 工程值
def _convert_raw_to_engineering(self, raw_value: int, tag: TagPoint) -> float:
    return raw_value * tag.scale_factor + tag.offset

# 工程值 → 原始值
def _convert_engineering_to_raw(self, value: float, tag: TagPoint) -> int:
    return int((value - tag.offset) / tag.scale_factor)
```

### 4.2 AgentService（LLM Agent 服务）

**职责**: 自然语言解析与工具调用

```python
class AgentService:
    def __init__(self, db: Session):
        self.db = db
        self.llm = ChatOpenAI(...)  # LLM 客户端
        self.executor = AgentExecutor(...)  # Agent 执行器

    def chat(self, user_id: int, message: str, session_id: str = None) -> Dict:
        """同步对话"""

    async def stream_chat(self, user_id: int, message: str, session_id: str = None):
        """流式对话，通过 SSE 返回"""

    def _get_or_create_session(self, user_id: int, session_id: str = None) -> AgentSession:
        """获取或创建会话"""
```

#### LangChain 工具定义

```python
@tool
def search_device(keyword: str) -> str:
    """
    搜索设备。
    输入：设备关键词（可为空，返回所有设备）
    输出：匹配的设备列表，包含 device_id、match_score
    """

@tool
def search_tag_mapping(device_id: int, query: str) -> str:
    """
    在指定设备下搜索点位。
    输入：device_id（必填）、query（点位关键词）
    输出：匹配的点位列表
    """

@tool
def read_plc(device_id: int, tag_name: str) -> str:
    """
    读取 PLC 点位值。
    返回：当前数值及单位
    """

@tool
def write_plc(device_id: int, tag_name: str, value: float) -> str:
    """
    写入 PLC 点位值。
    返回：操作结果
    """

@tool
def adjust_plc(device_id: int, tag_name: str, delta: float) -> str:
    """
    调整参数增量值。
    delta：正数增加，负数减少
    """

@tool
def confirm_operation() -> str:
    """
    确认执行待确认的操作。
    """

@tool
def cancel_operation() -> str:
    """
    取消待确认的操作。
    """
```

#### 流式事件类型

```python
# SSE 事件类型
{
    "type": "session",        # 会话创建
    "session_id": "uuid"
}
{
    "type": "token",          # 文本 token
    "content": "当前"
}
{
    "type": "action_start",   # 工具调用开始
    "action": {"tool": "search_device", "args": {"keyword": "空调"}}
}
{
    "type": "action_end",     # 工具调用结束
    "action": {"tool": "search_device", "result": "找到 1 个设备..."}
}
{
    "type": "done",           # 完成
    "reply": "智能空调当前温度为 26°C",
    "actions": [...]
}
{
    "type": "error",          # 错误
    "error": "LLM 服务不可用"
}
```

### 4.3 ConnectionPool（连接池服务）

**职责**: Modbus 连接管理

```python
class ModbusConnectionPool:
    def __init__(self, max_connections_per_device: int = 5):
        self._pools: Dict[int, Queue] = {}           # {device_id: Queue[Client]}
        self._device_configs: Dict[int, Device] = {}  # 设备配置缓存
        self._lock = threading.Lock()

    def add_device(self, device: Device) -> bool:
        """添加设备到连接池，创建多个连接"""

    def remove_device(self, device_id: int):
        """移除设备，关闭所有连接"""

    def acquire(self, device_id: int, timeout: float = 10) -> IModbusClient:
        """获取连接（阻塞）"""

    def release(self, device_id: int, client: IModbusClient):
        """释放连接回池"""

    def health_check(self, device_id: int) -> dict:
        """健康检查"""
        return {
            "healthy": available > 0,
            "available_connections": available,
            "max_connections": self.max_connections
        }
```

### 4.4 ClientFactory（客户端工厂）

**职责**: 创建不同协议的 Modbus 客户端

```python
class IModbusClient(ABC):
    """Modbus 客户端抽象接口"""
    @abstractmethod
    def connect(self) -> bool: ...
    @abstractmethod
    def close(self): ...
    @abstractmethod
    def read_holding_registers(self, address, count, slave) -> Dict: ...
    @abstractmethod
    def write_single_register(self, address, value, slave) -> Dict: ...
    # ... 其他读写方法

class TcpModbusClient(IModbusClient):
    """Modbus TCP 客户端"""
    def __init__(self, host, port, timeout):
        self._client = ModbusTcpClient(host, port, timeout)

class RtuOverTcpClient(IModbusClient):
    """RTU over TCP 客户端"""
    def __init__(self, host, port, timeout):
        self._client = ModbusTcpClient(host, port, timeout, framer=ModbusRtuFramer)

class ModbusClientFactory:
    @staticmethod
    def create(connection_type: str, host: str, port: int, timeout: int) -> IModbusClient:
        if connection_type == "TCP":
            return TcpModbusClient(host, port, timeout)
        elif connection_type == "RTU_OVER_TCP":
            return RtuOverTcpClient(host, port, timeout)
```

---

## 5. LLM Agent 设计

### 5.1 系统提示词结构

系统提示词从外部文件加载 (`backend/config/system_prompt.md`)，包含以下核心部分：

```
## 核心职责
将用户的自然语言指令转化为精确的 PLC 读写操作。

## 安全原则（最高优先级）
1. 禁止执行超出设备物理限制的操作
2. 所有写入操作必须先经过范围校验
3. 涉及启动/停止的操作需要人工确认

## 执行流程（严格遵守）
### 步骤1：意图解析
- 设备关键词、点位关键词、操作类型、参数值

### 步骤2：设备匹配
- 调用 search_device(keyword)
- 处理消歧场景

### 步骤3：点位匹配
- 调用 search_tag_mapping(device_id, query)
- 处理消歧场景

### 步骤4：执行操作
- read_plc / write_plc / adjust_plc

### 步骤5：结果反馈

## 上下文理解（多轮对话）
- last_device, last_tag, last_operation
- 代词解析规则

## 消歧询问格式
## 用户回复解析规则
## 确认操作工具
## 反馈格式
## 禁止事项
```

### 5.2 消歧机制

```
┌─────────────────────────────────────────────────────────────┐
│                    Disambiguation Flow                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User Input: "查看空调温度"                                  │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────┐                                        │
│  │ search_device() │                                        │
│  │ keyword="空调"  │                                        │
│  └────────┬────────┘                                        │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────────────────────────────┐               │
│  │ Check results:                          │               │
│  │ - Count >= 2 AND score_diff <= 20?      │               │
│  │   → disambiguation_needed = true        │               │
│  │ - Count == 0?                           │               │
│  │   → disambiguation_needed = true        │               │
│  │ - Otherwise: unique match               │               │
│  └────────┬────────────────────────────────┘               │
│           │                                                 │
│     ┌─────┴─────┐                                          │
│     │           │                                          │
│  Unique     Disambiguation                                 │
│  Match      Needed                                         │
│     │           │                                          │
│     ▼           ▼                                          │
│  Continue    Return:                                       │
│  to next     "检测到多个设备匹配，请选择：                    │
│  step        1. 测试空调                                    │
│              2. 智能空调"                                   │
│                   │                                        │
│                   ▼                                        │
│           User: "2"                                        │
│                   │                                        │
│                   ▼                                        │
│           Continue with selected device                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 操作确认机制

```
┌─────────────────────────────────────────────────────────────┐
│                  Confirmation Flow                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  User Input: "把频率设为50Hz"                               │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────┐                                        │
│  │ write_plc()     │                                        │
│  └────────┬────────┘                                        │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────────────────────────────┐               │
│  │ Check confirmation required:            │               │
│  │ 1. tag.requires_confirmation == True?   │               │
│  │ 2. value > threshold?                   │               │
│  └────────┬────────────────────────────────┘               │
│           │                                                 │
│     ┌─────┴─────┐                                          │
│     │           │                                          │
│   Not        Required                                      │
│   Required   Confirmation                                   │
│     │           │                                          │
│     ▼           ▼                                          │
│  Execute     Return:                                       │
│  Write       "操作需要人工确认: 该点位配置为需要人工确认"    │
│                   │                                        │
│                   ▼                                        │
│           User: "确认执行"                                  │
│                   │                                        │
│                   ▼                                        │
│           confirm_operation()                              │
│                   │                                        │
│                   ▼                                        │
│           Execute Write                                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. FunASR 语音服务集成

### 6.1 概述

FunASR 是阿里达摩院开源的语音识别服务，设备控制模块通过 WebSocket 直接连接 FunASR Docker 服务，实现实时语音识别功能。

**架构特点**：
- 前端直接连接 FunASR 服务，不经过后端
- 基于 AudioWorklet 的音频处理
- 支持 2pass-offline 模式（实时流式 + 离线修正）
- 自动静音检测，无需手动停止

### 6.2 服务架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Frontend                                        │
│                                                                              │
│  ┌─────────────────┐     ┌─────────────────┐     ┌───────────────────────┐  │
│  │   Microphone    │────►│  AudioWorklet   │────►│   useFunASRWs         │  │
│  │   MediaStream   │     │  Processor      │     │   Composable          │  │
│  └─────────────────┘     └─────────────────┘     └───────────┬───────────┘  │
│                                                          │                  │
│                          ┌───────────────────────────────┘                  │
│                          │                                                  │
│                          ▼                                                  │
│                  ┌───────────────────┐                                      │
│                  │   Chat Panel      │                                      │
│                  │   输入框填充      │                                      │
│                  └───────────────────┘                                      │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                │ WebSocket (ws://host:10095)
                                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                         FunASR Docker Service                                 │
│                                                                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │   Paraformer    │  │     VAD         │  │     Punctuation             │  │
│  │   语音识别模型   │  │   语音活动检测   │  │     标点恢复                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────────┘  │
│                                                                               │
│  模型路径: data/funasr-models/damo/                                          │
└───────────────────────────────────────────────────────────────────────────────┘
```

### 6.3 FunASR WebSocket 协议

#### 连接地址

| 环境 | 地址 |
|------|------|
| 开发环境 | `ws://localhost:10095` |
| 生产环境 | `wss://host/funasr-ws` (Nginx 代理) |

#### 初始化消息

```json
{
  "mode": "2pass-offline",
  "wav_name": "modbus_voice_input",
  "is_speaking": true,
  "audio_fs": 16000,
  "wav_format": "pcm",
  "chunk_size": [5, 10, 5]
}
```

#### 音频数据格式

- 格式: 二进制 PCM (Int16)
- 采样率: 16kHz
- 声道: 单声道
- 发送: WebSocket binary frame

#### 结束信号

```json
{
  "is_speaking": false
}
```

#### 识别结果消息

```json
{
  "text": "空调温度调到二十六度",
  "is_final": false,
  "mode": "2pass-offline",
  "stamp_sents": [
    {
      "start": 0,
      "end": 2000,
      "punc": "",
      "text_seg": "空调温度调到二十六度"
    }
  ]
}
```

### 6.4 AudioWorklet 处理器

**文件位置**: `frontend-new/public/workers/audio-processor.js`

#### 功能

1. **重采样**: 将原生采样率转换为 16kHz
2. **分块**: 每 600ms (9600 samples) 发送一次
3. **静音检测**: RMS 音量检测，自动结束录音
4. **格式转换**: Float32 → Int16 PCM

#### 静音检测配置

| 参数 | 默认值 | 描述 |
|------|--------|------|
| silenceThreshold | 0.01 | RMS 阈值，低于此值视为静音 |
| silenceDuration | 1.5s | 持续静音时间，超过后自动结束 |

```javascript
// 配置更新
workletNode.port.postMessage({
  type: 'config',
  silenceThreshold: 0.02,
  silenceDuration: 2.0
});
```

### 6.5 前端集成代码

#### Composable 接口

```typescript
// src/composables/modbus/use-funasr-ws.ts
export function useFunASRWs(options: UseFunASRWsOptions = {}) {
  const isConnected = ref(false);
  const isRecording = ref(false);
  const tempResult = ref('');    // 实时识别结果
  const finalResult = ref('');   // 最终结果

  // 开始录音
  async function startRecording(): Promise<boolean> { ... }

  // 停止录音
  function stopRecording(): void { ... }

  // 连接服务
  async function connect(): Promise<boolean> { ... }

  // 断开连接
  function disconnect(): void { ... }

  // 更新静音检测配置
  function updateSilenceConfig(threshold: number, duration: number): void { ... }

  return {
    isConnected,
    isRecording,
    tempResult,
    finalResult,
    startRecording,
    stopRecording,
    connect,
    disconnect,
    updateSilenceConfig
  };
}
```

#### 在 Chat Panel 中使用

```vue
<script setup>
import { useFunASRWs } from '@/composables/modbus/use-funasr-ws';

const {
  isRecording,
  tempResult,
  startRecording,
  stopRecording
} = useFunASRWs({
  onResult: (text, isFinal) => {
    if (isFinal) {
      inputMessage.value = text;
    }
  },
  onError: (error) => {
    message.error('语音识别失败: ' + error.message);
  }
});

// 语音按钮点击
function handleVoiceClick() {
  if (isRecording.value) {
    stopRecording();
  } else {
    startRecording();
  }
}
</script>

<template>
  <div class="input-actions">
    <!-- 语音输入按钮 -->
    <a-button @click="handleVoiceClick" :type="isRecording ? 'primary' : 'default'">
      <template #icon>
        <SvgIcon :icon="isRecording ? 'mdi:stop' : 'mdi:microphone'" />
      </template>
    </a-button>

    <!-- 实时识别结果预览 -->
    <div v-if="tempResult" class="voice-preview">
      {{ tempResult }}
    </div>
  </div>
</template>
```

### 6.6 部署配置

#### Docker Compose

```yaml
# docker-compose.yml
services:
  funasr:
    image: registry.cn-hangzhou.aliyuncs.com/funasr_repo/funasr:funasr-runtime-sdk-cpu-latest
    container_name: funasr
    ports:
      - "10095:10095"
    volumes:
      - ./data/funasr-models:/workspace/models
    environment:
      - MODEL_DIR=/workspace/models
    restart: unless-stopped
```

#### Nginx 代理配置

```nginx
# 生产环境 WebSocket 代理
location /funasr-ws {
    proxy_pass http://funasr:10095;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 86400;
}
```

### 6.7 识别模式说明

| 模式 | 描述 | 适用场景 |
|------|------|----------|
| 2pass-offline | 实时流式 + 离线修正 | 设备控制（推荐） |
| 2pass-online | 纯实时流式 | 低延迟场景 |
| offline | 纯离线识别 | 高精度场景 |

**2pass-offline 工作流程**：

1. 用户开始说话
2. 实时推送识别结果（2pass-online）
3. 用户停止说话后，离线模型修正结果（2pass-offline）
4. 返回最终识别文本

---

## 7. 前端架构设计

### 6.1 组件结构

```
src/views/modbus/control/
├── index.vue                    # 主控制页面
├── components/
│   ├── DeviceTree.vue          # 设备树组件（已内联）
│   ├── ChatPanel.vue           # 对话面板（已内联）
│   ├── DeviceDetailDrawer.vue  # 设备详情抽屉（已内联）
│   └── ChatHistorySidebar.vue  # 历史侧边栏（已内联）
```

### 6.2 状态管理 (Pinia Store)

```typescript
// src/store/modules/modbus/index.ts
export const useModbusStore = defineStore('modbus-store', () => {
  // State
  const devices = ref<Device[]>([]);
  const currentDevice = ref<Device | null>(null);
  const tagPoints = ref<TagPoint[]>([]);
  const deviceTagPointsMap = ref<Record<number, TagPoint[]>>({});
  const messages = ref<ChatMessage[]>([]);
  const sessionId = ref<string>('');
  const chatLoading = ref(false);
  const wsConnected = ref(false);
  const chatHistory = ref<ChatSession[]>([]);

  // Getters
  const onlineDevices = computed(() => devices.value.filter(d => d.status === 'online'));
  const deviceTree = computed(() => {
    // 按 group_name 分组
    const groups: Record<string, Device[]> = {};
    devices.value.forEach(device => {
      const group = device.group_name || '默认分组';
      if (!groups[group]) groups[group] = [];
      groups[group].push(device);
    });
    return groups;
  });

  // Actions
  async function loadDevices(params?) { ... }
  async function sendMessageStream(content: string) { ... }
  async function saveCurrentChatToHistory() { ... }
  // ...
});
```

### 6.3 WebSocket 连接

```typescript
// src/composables/modbus/use-modbus-ws.ts
export function useModbusWs() {
  const ws = ref<WebSocket | null>(null);
  const reconnectAttempts = ref(0);
  const maxReconnectAttempts = 5;

  function connect() {
    const wsUrl = `ws://${host}/ws/modbus?token=${token}`;
    ws.value = new WebSocket(wsUrl);

    ws.value.onmessage = event => {
      const message = JSON.parse(event.data);
      handleMessage(message);
    };
  }

  function handleMessage(message: WebSocketMessage) {
    switch (message.type) {
      case 'device_status':
        modbusStore.updateDeviceStatus(message.data);
        break;
      case 'tag_value':
        modbusStore.updateTagValue(message.data);
        break;
    }
  }

  return { connect, disconnect };
}
```

### 6.4 SSE 流式对话

```typescript
// src/service/api/modbus.ts
export function fetchChatStream(
  data: { message: string; session_id?: string },
  onEvent: (event) => void,
  onError?: (error: Error) => void
) {
  const controller = new AbortController();

  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(data),
    signal: controller.signal
  }).then(async response => {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const event = JSON.parse(line.slice(6));
          onEvent(event);
        }
      }
    }
  });

  return () => controller.abort();  // 返回取消函数
}
```

---

## 8. API 设计

### 7.1 RESTful API 规范

**基础路径**: `/api/modbus`

**认证方式**: Bearer Token (JWT)

**响应格式**:
```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

### 7.2 核心接口定义

#### 连接设备

```
POST /control/connect
Request Body: [device_id1, device_id2, ...]  // 可选，为空则连接全部
Response: {
  "message": "已成功连接所有 2 个设备",
  "results": [
    {"device_id": 1, "device_name": "空调", "success": true},
    {"device_id": 2, "device_name": "风机", "success": false, "error": "连接超时"}
  ]
}
```

#### 流式对话

```
POST /control/chat/stream
Request Body: {"message": "空调温度", "session_id": "optional"}
Response: SSE 流
  data: {"type": "session", "session_id": "uuid"}
  data: {"type": "token", "content": "智能"}
  data: {"type": "token", "content": "空调"}
  data: {"type": "action_start", "action": {"tool": "search_device", "args": {...}}}
  data: {"type": "action_end", "action": {"tool": "search_device", "result": "..."}}
  data: {"type": "done", "reply": "智能空调当前温度为 26°C", "actions": [...]}
```

---

## 9. 配置管理

### 8.1 环境变量

```bash
# Modbus 配置
MODBUS_POOL_SIZE=5
MODBUS_CONNECT_TIMEOUT=5
MODBUS_READ_TIMEOUT=10
MODBUS_POLL_ENABLED=true
MODBUS_LOG_RETENTION_DAYS=30
MODBUS_PENDING_EXPIRE_MINUTES=10

# LLM 配置
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-xxx
LLM_MODEL=gpt-4o-mini
LLM_SESSION_TTL_MINUTES=10
```

### 8.2 热更新配置

**快捷指令**: `backend/config/quick_commands.json`
```json
{
  "quick_commands": [
    {
      "id": "view_status",
      "label": {"zh": "查看状态", "en": "View Status"},
      "text": {"zh": "查看所有设备状态", "en": "View all device status"}
    }
  ]
}
```

**系统提示词**: `backend/config/system_prompt.md`

---

## 10. 安全设计

### 9.1 权限控制

```python
# API 权限注解
@router.post("/connect")
async def connect_devices(
    user: User = Depends(check_permission("modbus:control:write"))
):
    ...
```

### 9.2 值范围校验

```python
# PLCService.write()
if not (tag.min_value <= value <= tag.max_value):
    return {
        "success": False,
        "message": f"值 {value} 超出安全范围 [{tag.min_value}, {tag.max_value}]"
    }
```

### 9.3 操作确认

```python
def _check_confirmation_required(self, tag: TagPoint, value: float) -> Dict:
    # 强制确认点位
    if tag.requires_confirmation:
        return {"required": True, "reason": "该点位配置为需要人工确认"}

    # 阈值确认
    if tag.confirmation_threshold:
        range_size = tag.max_value - tag.min_value
        threshold_value = tag.min_value + range_size * tag.confirmation_threshold
        if abs(value) >= threshold_value:
            return {"required": True, "reason": f"值 {value} 超过安全阈值"}

    return {"required": False}
```

### 9.4 WebSocket 认证

```python
# WebSocket 连接时验证 Token
@app.websocket("/ws/modbus")
async def websocket_endpoint(websocket: WebSocket, token: str):
    user = verify_token(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    ...
```

---

## 11. 错误处理

### 10.1 错误码定义

| 错误码 | 描述 |
|--------|------|
| 400 | 请求参数错误 |
| 401 | 未授权 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
| 503 | LLM 服务不可用 |

### 10.2 异常处理

```python
# PLCService 中的异常处理
try:
    result = client.read_holding_registers(address, count, slave)
except ModbusException as e:
    command_log.status = "failed"
    command_log.error_message = str(e)
    self.db.commit()
    return {"success": False, "message": str(e)}
finally:
    connection_pool.release(device_id, client)
```

---

## 12. 性能优化

### 11.1 连接池

- 每设备独立连接池，避免资源竞争
- 连接复用，减少 TCP 握手开销
- 健康检查，自动剔除无效连接

### 11.2 流式输出

- SSE 实现流式响应，首字延迟 < 3s
- 前端逐字渲染，提升用户体验

### 11.3 前端优化

- 虚拟滚动处理长消息列表
- 防抖处理输入框
- WebSocket 心跳保活

---

## 13. 扩展性设计

### 12.1 新增工具

1. 在 `AgentService` 中定义新工具：
```python
@tool
def new_tool(param: str) -> str:
    """工具描述"""
    return result
```

2. 添加到工具列表
3. 更新系统提示词

### 12.2 新增连接类型

1. 实现 `IModbusClient` 接口
2. 在 `ModbusClientFactory` 中注册

### 12.3 新增寄存器类型

1. 在 `PLCService` 中添加读写逻辑
2. 更新 Schema 枚举

---

## 14. 部署架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Nginx Reverse Proxy                    │
│  - /api/*     → FastAPI Backend                            │
│  - /ws/*      → WebSocket Upgrade                          │
│  - /*         → Vue Frontend                               │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
    ┌─────▼─────┐       ┌─────▼─────┐       ┌─────▼─────┐
    │  Frontend │       │  Backend  │       │  Database │
    │  (Vue 3)  │       │ (FastAPI) │       │ (SQLite)  │
    └───────────┘       └─────┬─────┘       └───────────┘
                              │
                    ┌─────────┼─────────┐
                    │         │         │
              ┌─────▼─────┐ ┌─▼───┐ ┌───▼───┐
              │  LLM API  │ │ PLC │ │ PLC   │
              │ (OpenAI)  │ │ #1  │ │ #2    │
              └───────────┘ └─────┘ └───────┘
```

---

## 15. 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|----------|
| 1.0 | 2026-03-22 | 初始版本 |
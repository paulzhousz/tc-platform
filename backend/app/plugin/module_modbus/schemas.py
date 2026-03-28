"""
Modbus 控制模块 Pydantic Schemas
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ==================== 枚举类型 ====================


class ConnectionType(str, Enum):
    TCP = "TCP"
    RTU_OVER_TCP = "RTU_OVER_TCP"


class RegisterType(str, Enum):
    HOLDING = "holding"
    INPUT = "input"
    COIL = "coil"
    DISCRETE = "discrete"


class DataType(str, Enum):
    INT16 = "INT16"
    UINT16 = "UINT16"
    INT32 = "INT32"
    UINT32 = "UINT32"
    FLOAT = "FLOAT"
    BOOL = "BOOL"


class AccessType(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    READ_WRITE = "READ_WRITE"


class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"


class CommandStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConfirmStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ActionStatus(str, Enum):
    """ActionStep 执行状态"""

    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    CANCELLED = "cancelled"


# ==================== Device Schemas ====================


class DeviceBase(BaseModel):
    name: str = Field(..., max_length=100, description="设备名称")
    code: str = Field(..., max_length=50, description="设备编码")
    description: str | None = Field(None, description="设备描述")
    group_name: str | None = Field(None, max_length=50, description="设备分组")
    connection_type: ConnectionType = Field(
        default=ConnectionType.TCP, description="连接类型"
    )
    host: str = Field(..., max_length=100, description="IP 地址")
    port: int = Field(default=502, ge=1, le=65535, description="端口")
    slave_id: int = Field(default=1, ge=1, description="从站地址")
    baud_rate: int | None = Field(None, description="波特率")
    parity: str | None = Field(None, max_length=10, description="校验位")


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = None
    group_name: str | None = Field(None, max_length=50)
    connection_type: ConnectionType | None = None
    host: str | None = Field(None, max_length=100)
    port: int | None = Field(None, ge=1, le=65535)
    slave_id: int | None = Field(None, ge=1)
    baud_rate: int | None = None
    parity: str | None = Field(None, max_length=10)


class DeviceResponse(DeviceBase):
    id: int
    device_status: DeviceStatus
    last_seen: datetime | None
    created_time: datetime
    updated_time: datetime | None

    class Config:
        from_attributes = True


class DeviceListResponse(BaseModel):
    items: list[DeviceResponse]
    total: int


# ==================== TagPoint Schemas ====================


class TagPointBase(BaseModel):
    name: str = Field(..., max_length=100, description="点位名称")
    code: str = Field(..., max_length=50, description="点位编码")
    description: str | None = Field(None, description="点位描述")
    address: int = Field(..., ge=0, description="寄存器地址")
    register_type: RegisterType = Field(
        default=RegisterType.HOLDING, description="寄存器类型"
    )
    data_type: DataType = Field(default=DataType.INT16, description="数据类型")
    byte_order: str = Field(default="big", max_length=10, description="字节序")
    access_type: AccessType = Field(
        default=AccessType.READ_WRITE, description="访问类型"
    )
    min_value: float = Field(default=0, description="最小值")
    max_value: float = Field(default=100, description="最大值")
    unit: str | None = Field(None, max_length=20, description="单位")
    scale_factor: float = Field(default=1.0, description="缩放因子")
    offset: float = Field(default=0.0, description="偏移量")
    aliases: list[str] | None = Field(default=[], description="语义别名")
    requires_confirmation: bool = Field(default=False, description="是否需要确认")
    confirmation_threshold: float | None = Field(None, description="确认阈值")
    sort_order: int = Field(default=0, description="排序")
    is_active: bool = Field(default=True, description="是否启用")


class TagPointCreate(TagPointBase):
    pass


class TagPointUpdate(BaseModel):
    name: str | None = Field(None, max_length=100)
    description: str | None = None
    address: int | None = Field(None, ge=0)
    register_type: RegisterType | None = None
    data_type: DataType | None = None
    access_type: AccessType | None = None
    min_value: float | None = None
    max_value: float | None = None
    unit: str | None = Field(None, max_length=20)
    scale_factor: float | None = None
    offset: float | None = None
    aliases: list[str] | None = None
    requires_confirmation: bool | None = None
    confirmation_threshold: float | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class TagPointResponse(TagPointBase):
    id: int
    device_id: int
    current_value: float | None
    last_updated: datetime | None
    created_time: datetime

    class Config:
        from_attributes = True


class TagPointListResponse(BaseModel):
    items: list[TagPointResponse]
    total: int


# ==================== CommandLog Schemas ====================


class CommandLogResponse(BaseModel):
    id: int
    user_id: int
    session_id: str | None
    device_id: int | None
    tag_id: int | None
    action: str
    request_value: float | None
    actual_value: float | None
    log_status: CommandStatus
    error_message: str | None
    confirmation_required: bool
    confirmed_by: int | None
    confirmed_at: datetime | None
    ai_reasoning: str | None
    user_input: str | None
    retry_count: int
    execution_time: float | None
    created_time: datetime
    executed_at: datetime | None

    class Config:
        from_attributes = True


class CommandLogListResponse(BaseModel):
    items: list[CommandLogResponse]
    total: int


class CommandLogFilter(BaseModel):
    device_id: int | None = None
    user_id: int | None = None
    action: str | None = None
    status: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


# ==================== PendingConfirm Schemas ====================


class PendingConfirmResponse(BaseModel):
    id: int
    command_log_id: int | None
    device_name: str | None
    tag_name: str | None
    target_value: float | None
    unit: str | None
    confirm_status: ConfirmStatus
    expires_at: datetime | None
    reviewed_by: int | None
    reviewed_at: datetime | None
    review_comment: str | None
    user_input: str | None
    ai_explanation: str | None
    created_time: datetime

    class Config:
        from_attributes = True


class PendingConfirmListResponse(BaseModel):
    items: list[PendingConfirmResponse]
    total: int


class ConfirmAction(BaseModel):
    comment: str | None = Field(None, description="确认/拒绝备注")


# ==================== Agent Schemas ====================


class ActionStep(BaseModel):
    """AI 执行步骤"""

    tool: str = Field(..., description="工具名称")
    args: dict[str, Any] = Field(default_factory=dict, description="工具参数")
    status: str | None = Field(None, description="执行状态")
    started_at: str | None = Field(None, description="开始时间")
    finished_at: str | None = Field(None, description="结束时间")
    duration_ms: int | None = Field(None, description="执行耗时(毫秒)")
    result: str | None = Field(None, description="执行结果摘要")
    error: str | None = Field(None, description="错误信息")
    data: dict[str, Any] | None = Field(None, description="结构化结果数据")
    command_log_id: int | None = Field(None, description="关联的操作日志ID")


class ChatRequest(BaseModel):
    message: str = Field(..., description="用户消息")
    session_id: str | None = Field(None, description="会话 ID")


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    actions: list[ActionStep] | None = Field(default=None, description="执行步骤")
    reasoning: str | None = None
    requires_confirmation: bool = False
    pending_confirm_id: int | None = None


class ReadRequest(BaseModel):
    device_id: int
    tag_name: str


class WriteRequest(BaseModel):
    device_id: int
    tag_name: str
    value: float


class ReadResponse(BaseModel):
    device_id: int
    tag_name: str
    value: float
    raw_value: int
    unit: str | None


class WriteResponse(BaseModel):
    device_id: int
    tag_name: str
    value: float
    unit: str | None
    success: bool
    message: str


# ==================== WebSocket Message Schemas ====================


class WSMessage(BaseModel):
    type: str  # device_status, tag_value, operation_result, pending_confirm
    data: dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)


class DeviceStatusMessage(BaseModel):
    device_id: int
    device_name: str
    status: DeviceStatus
    last_seen: datetime | None


class TagValueMessage(BaseModel):
    device_id: int
    tag_id: int
    tag_name: str
    value: float
    unit: str | None
    previous_value: float | None


class OperationResultMessage(BaseModel):
    command_log_id: int
    user_id: int
    success: bool
    message: str


class PendingConfirmMessage(BaseModel):
    pending_confirm_id: int
    device_name: str
    tag_name: str
    target_value: float
    unit: str | None
    user_input: str | None
    ai_explanation: str | None
    expires_at: datetime | None


# ==================== Chat History Schemas ====================


class ChatMessageItem(BaseModel):
    """单条聊天消息"""

    role: str = Field(..., description="角色: user/assistant")
    content: str = Field(..., description="消息内容")
    timestamp: str = Field(..., description="时间戳")
    actions: list[ActionStep] | None = Field(None, description="AI 执行步骤")


class ChatHistoryCreate(BaseModel):
    """创建聊天历史"""

    session_id: str = Field(..., description="会话 ID")
    messages: list[ChatMessageItem] = Field(..., description="消息列表")
    device_count: int = Field(default=0, description="设备数量")
    device_names: list[str] = Field(default_factory=list, description="设备名称列表")


class ChatHistoryResponse(BaseModel):
    """聊天历史响应"""

    id: int
    session_id: str
    title: str | None
    device_count: int
    device_names: list[str]
    start_time: datetime
    end_time: datetime | None
    created_time: datetime

    class Config:
        from_attributes = True


class ChatHistoryDetailResponse(ChatHistoryResponse):
    """聊天历史详情（包含消息内容）"""

    messages: list[ChatMessageItem]


class ChatHistoryListResponse(BaseModel):
    """聊天历史列表响应"""

    items: list[ChatHistoryResponse]
    total: int

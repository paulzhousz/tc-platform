"""
Modbus 控制模块数据模型

设计说明：
- Device: 设备是共享工业资源，不继承 UserMixin，但记录 created_id 标识创建者
- TagPoint: 属于设备，继承共享属性
- CommandLog: 记录 PLC 操作审计，需要 user_id 标识操作人
- PendingConfirm: 待确认操作，需要 user_id 标识操作发起人和审核人
- AgentSession: 用户级别会话隔离
- ChatHistory: 用户级别历史记录
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import ModelMixin


class DeviceModel(ModelMixin):
    """
    PLC 设备模型

    设备是共享工业资源，所有用户应能看到和控制同一批设备。
    因此不继承 UserMixin，但通过 created_id 记录创建者。
    """

    __tablename__ = "modbus_devices"
    __table_args__ = {"comment": "PLC 设备表"}

    # 基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="设备名称")
    code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="设备编码"
    )
    group_name: Mapped[str | None] = mapped_column(String(50), comment="分组名称")

    # 连接配置
    connection_type: Mapped[str] = mapped_column(
        String(20), default="TCP", comment="连接类型(TCP/RTU_OVER_TCP)"
    )
    host: Mapped[str] = mapped_column(String(100), nullable=False, comment="IP地址")
    port: Mapped[int] = mapped_column(Integer, default=502, comment="端口")
    slave_id: Mapped[int] = mapped_column(Integer, default=1, comment="从站ID")

    # RTU 参数（RTU_OVER_TCP 使用）
    baud_rate: Mapped[int | None] = mapped_column(Integer, default=9600, comment="波特率")
    parity: Mapped[str | None] = mapped_column(String(10), default="N", comment="校验位")

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    device_status: Mapped[str] = mapped_column(
        String(20), default="offline", comment="设备状态(online/offline/error)"
    )
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, comment="最后在线时间")

    # 创建者（记录谁创建了这个设备，但设备本身是共享的）
    created_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("sys_user.id", ondelete="SET NULL"),
        comment="创建人ID",
    )

    # 关系
    tags: Mapped[list["TagPointModel"]] = relationship(
        "TagPointModel", back_populates="device", cascade="all, delete-orphan"
    )


class TagPointModel(ModelMixin):
    """
    设备点位模型

    属于设备，继承设备的共享属性。
    """

    __tablename__ = "modbus_tags"
    __table_args__ = {"comment": "设备点位表"}

    device_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("modbus_devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="设备ID",
    )

    # 基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="点位名称")
    code: Mapped[str] = mapped_column(String(50), nullable=False, comment="点位编码")

    # Modbus 地址
    address: Mapped[int] = mapped_column(Integer, nullable=False, comment="寄存器地址")
    register_type: Mapped[str] = mapped_column(
        String(20), default="holding", comment="寄存器类型(holding/input/coil/discrete)"
    )

    # 数据类型
    data_type: Mapped[str] = mapped_column(
        String(20), default="INT16", comment="数据类型(INT16/UINT16/INT32/FLOAT/BOOL)"
    )
    byte_order: Mapped[str] = mapped_column(String(10), default="big", comment="字节序")

    # 访问控制
    access_type: Mapped[str] = mapped_column(
        String(20), default="READ_WRITE", comment="访问类型(READ/WRITE/READ_WRITE)"
    )

    # 数值范围与单位
    min_value: Mapped[float] = mapped_column(Float, default=0, comment="最小值")
    max_value: Mapped[float] = mapped_column(Float, default=100, comment="最大值")
    unit: Mapped[str | None] = mapped_column(String(20), comment="单位")

    # 数值转换（工程值 = 原始值 * scale_factor + offset）
    scale_factor: Mapped[float] = mapped_column(Float, default=1.0, comment="缩放因子")
    offset: Mapped[float] = mapped_column(Float, default=0.0, comment="偏移量")

    # 语义映射（用于 AI 理解）
    aliases: Mapped[list | None] = mapped_column(JSON, comment="语义别名列表")

    # 安全策略
    requires_confirmation: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否需要确认"
    )
    confirmation_threshold: Mapped[float | None] = mapped_column(
        Float, comment="确认阈值比例"
    )

    # 缓存（按需刷新）
    current_value: Mapped[float | None] = mapped_column(Float, comment="当前值")
    last_updated: Mapped[datetime | None] = mapped_column(
        DateTime, comment="最后更新时间"
    )

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序")

    # 关系
    device: Mapped["DeviceModel"] = relationship("DeviceModel", back_populates="tags")


class CommandLogModel(ModelMixin):
    """
    PLC 操作审计日志

    用于记录 PLC 设备的读写操作详情，与系统的 HTTP 请求审计是独立的两个日志体系。
    """

    __tablename__ = "modbus_command_logs"
    __table_args__ = {"comment": "PLC 操作审计日志表"}

    # 操作来源
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_user.id"), nullable=False, index=True, comment="操作用户ID"
    )
    session_id: Mapped[str | None] = mapped_column(String(50), comment="Agent 会话ID")

    # 操作目标
    device_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("modbus_devices.id"), comment="设备ID"
    )
    tag_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("modbus_tags.id"), comment="点位ID"
    )

    # 操作内容
    action: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="操作类型(READ/WRITE)"
    )
    request_value: Mapped[float | None] = mapped_column(Float, comment="请求值")
    actual_value: Mapped[float | None] = mapped_column(Float, comment="实际值")

    # 结果
    log_status: Mapped[str] = mapped_column(
        String(20), default="pending", comment="状态(pending/success/failed/cancelled)"
    )
    error_message: Mapped[str | None] = mapped_column(Text, comment="错误信息")

    # 确认信息
    confirmation_required: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否需要确认"
    )
    confirmed_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sys_user.id"), comment="确认人ID"
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, comment="确认时间")

    # AI 信息
    ai_reasoning: Mapped[str | None] = mapped_column(Text, comment="AI 推理过程")
    user_input: Mapped[str | None] = mapped_column(Text, comment="用户原始输入")

    # 执行详情
    retry_count: Mapped[int] = mapped_column(Integer, default=0, comment="重试次数")
    execution_time: Mapped[float | None] = mapped_column(Float, comment="执行耗时(毫秒)")
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, comment="执行时间")


class PendingConfirmModel(ModelMixin):
    """
    待人工确认的操作
    """

    __tablename__ = "modbus_pending_confirms"
    __table_args__ = {"comment": "待确认操作表"}

    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sys_user.id"), comment="创建者用户ID"
    )
    command_log_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("modbus_command_logs.id"), comment="关联命令日志ID"
    )

    # 操作详情（冗余存储，便于展示）
    device_name: Mapped[str | None] = mapped_column(String(100), comment="设备名称")
    tag_name: Mapped[str | None] = mapped_column(String(100), comment="点位名称")
    target_value: Mapped[float | None] = mapped_column(Float, comment="目标值")
    unit: Mapped[str | None] = mapped_column(String(20), comment="单位")

    # 状态
    confirm_status: Mapped[str] = mapped_column(
        String(20), default="pending", comment="状态(pending/confirmed/rejected/expired)"
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, comment="过期时间")

    # 审核信息
    reviewed_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("sys_user.id"), comment="审核人ID"
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, comment="审核时间")
    review_comment: Mapped[str | None] = mapped_column(Text, comment="审核备注")

    # AI 信息
    user_input: Mapped[str | None] = mapped_column(Text, comment="用户输入")
    ai_explanation: Mapped[str | None] = mapped_column(Text, comment="AI 解释")


class AgentSessionModel(ModelMixin):
    """
    LLM Agent 会话

    用于用户级别的会话隔离和上下文管理。
    """

    __tablename__ = "modbus_agent_sessions"
    __table_args__ = {"comment": "Agent 会话表"}

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_user.id"), nullable=False, index=True, comment="用户ID"
    )
    session_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True, comment="会话ID"
    )

    # 上下文（简单字段，兼容旧数据）
    last_device_id: Mapped[int | None] = mapped_column(Integer, comment="最后操作设备ID")
    last_tag_id: Mapped[int | None] = mapped_column(Integer, comment="最后操作点位ID")

    # 详细操作上下文
    # 结构: {"last_device": {...}, "last_tag": {...}, "last_operation": {...}}
    operation_context: Mapped[dict | None] = mapped_column(JSON, comment="操作上下文")

    # 对话历史
    chat_history: Mapped[list | None] = mapped_column(JSON, comment="对话历史")

    # 时间
    last_active: Mapped[datetime | None] = mapped_column(
        DateTime, default=func.now(), comment="最后活跃时间"
    )
    ttl_minutes: Mapped[int] = mapped_column(Integer, default=10, comment="会话TTL(分钟)")


class ChatHistoryModel(ModelMixin):
    """
    用户聊天历史（长期存储）
    """

    __tablename__ = "modbus_chat_history"
    __table_args__ = {"comment": "聊天历史表"}

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sys_user.id"), nullable=False, index=True, comment="用户ID"
    )
    session_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True, comment="会话ID"
    )

    # 预览信息
    title: Mapped[str | None] = mapped_column(String(200), comment="首条用户消息摘要")

    # 对话内容
    messages: Mapped[list] = mapped_column(
        JSON, nullable=False, comment="消息列表"
    )

    # 设备上下文
    device_count: Mapped[int] = mapped_column(Integer, default=0, comment="涉及设备数")
    device_names: Mapped[list | None] = mapped_column(JSON, comment="设备名称列表")

    # 时间
    start_time: Mapped[datetime | None] = mapped_column(DateTime, comment="开始时间")
    end_time: Mapped[datetime | None] = mapped_column(DateTime, comment="结束时间")

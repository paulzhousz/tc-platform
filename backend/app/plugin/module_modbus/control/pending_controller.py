"""
Modbus 待确认操作 API 控制器
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import ErrorResponse, SuccessResponse
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute
from app.plugin.module_modbus.control.services.plc_service import PLCService
from app.plugin.module_modbus.models import DeviceModel, PendingConfirmModel, TagPointModel
from app.plugin.module_modbus.schemas import (
    ConfirmAction,
    PendingConfirmListResponse,
    PendingConfirmResponse,
)

PendingRouter = APIRouter(
    route_class=OperationLogRoute, prefix="/pending", tags=["Modbus待确认操作"]
)


@PendingRouter.get(
    "/list",
    summary="获取待确认操作列表",
    description="获取待确认操作列表",
    response_model=PendingConfirmListResponse,
)
async def list_pending(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:write"]))],
    status: Annotated[str | None, Body(description="状态筛选")] = None,
) -> JSONResponse:
    """获取待确认操作列表"""
    stmt = select(PendingConfirmModel)

    if status:
        stmt = stmt.where(PendingConfirmModel.status == status)
    else:
        # 默认只显示待处理的
        stmt = stmt.where(PendingConfirmModel.status == "pending")

    stmt = stmt.order_by(PendingConfirmModel.created_at.desc())
    pendings = (await auth.db.execute(stmt)).scalars().all()

    items = [PendingConfirmResponse.model_validate(p) for p in pendings]
    return SuccessResponse(
        data=PendingConfirmListResponse(items=items, total=len(items)), msg="获取成功"
    )


@PendingRouter.post(
    "/{pending_id}/confirm",
    summary="确认操作",
    description="确认执行待确认操作",
)
async def confirm_operation(
    pending_id: Annotated[int, Path(description="待确认ID")],
    data: ConfirmAction,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:write"]))],
) -> JSONResponse:
    """确认操作"""
    stmt = select(PendingConfirmModel).where(PendingConfirmModel.id == pending_id)
    pending = (await auth.db.execute(stmt)).scalar_one_or_none()

    if not pending:
        return ErrorResponse(msg="待确认记录不存在")

    if pending.status != "pending":
        return ErrorResponse(msg=f"该操作已处理，状态: {pending.status}")

    # 检查是否过期
    if pending.expires_at and datetime.now() > pending.expires_at:
        pending.status = "expired"
        await auth.db.commit()
        return ErrorResponse(msg="操作已过期")

    # 执行写入操作
    stmt = select(DeviceModel).where(DeviceModel.name == pending.device_name)
    device = (await auth.db.execute(stmt)).scalar_one_or_none()
    if not device:
        return ErrorResponse(msg=f"设备 '{pending.device_name}' 不存在")

    stmt = select(TagPointModel).where(
        TagPointModel.device_id == device.id, TagPointModel.name == pending.tag_name
    )
    tag = (await auth.db.execute(stmt)).scalar_one_or_none()
    if not tag:
        return ErrorResponse(msg=f"点位 '{pending.tag_name}' 不存在")

    plc_service = PLCService(auth.db)
    result = await plc_service.write(
        device_id=device.id,
        tag_code=tag.code,
        value=pending.target_value,
        user_id=auth.user.id,
    )

    # 更新待确认状态
    pending.status = "confirmed"
    pending.reviewed_by = auth.user.id
    pending.reviewed_at = datetime.now()
    pending.review_comment = data.comment
    await auth.db.commit()

    if result["success"]:
        return SuccessResponse(
            data={
                "message": "操作已确认并执行",
                "result": result,
            },
            msg="操作成功",
        )
    else:
        return ErrorResponse(msg=f"执行失败: {result['message']}")


@PendingRouter.post(
    "/{pending_id}/reject",
    summary="拒绝操作",
    description="拒绝执行待确认操作",
)
async def reject_operation(
    pending_id: Annotated[int, Path(description="待确认ID")],
    data: ConfirmAction,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:control:write"]))],
) -> JSONResponse:
    """拒绝操作"""
    stmt = select(PendingConfirmModel).where(PendingConfirmModel.id == pending_id)
    pending = (await auth.db.execute(stmt)).scalar_one_or_none()

    if not pending:
        return ErrorResponse(msg="待确认记录不存在")

    if pending.status != "pending":
        return ErrorResponse(msg=f"该操作已处理，状态: {pending.status}")

    # 更新状态
    pending.status = "rejected"
    pending.reviewed_by = auth.user.id
    pending.reviewed_at = datetime.now()
    pending.review_comment = data.comment
    await auth.db.commit()

    return SuccessResponse(msg="操作已拒绝")
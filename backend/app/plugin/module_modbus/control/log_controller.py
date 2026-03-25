"""
Modbus 操作日志 API 控制器
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import ErrorResponse, SuccessResponse
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute
from app.plugin.module_modbus.models import CommandLogModel
from app.plugin.module_modbus.schemas import (
    CommandLogListResponse,
    CommandLogResponse,
)

LogRouter = APIRouter(
    route_class=OperationLogRoute, prefix="/log", tags=["Modbus操作日志"]
)


@LogRouter.get(
    "/list",
    summary="获取操作日志列表",
    description="获取操作日志列表（支持筛选和分页）",
    response_model=CommandLogListResponse,
)
async def list_logs(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:log:query"]))],
    device_id: Annotated[int | None, Query(description="设备ID筛选")] = None,
    user_id: Annotated[int | None, Query(description="用户ID筛选")] = None,
    action: Annotated[str | None, Query(description="操作类型筛选")] = None,
    status: Annotated[str | None, Query(description="状态筛选")] = None,
    start_time: Annotated[datetime | None, Query(description="开始时间")] = None,
    end_time: Annotated[datetime | None, Query(description="结束时间")] = None,
    page: Annotated[int, Query(ge=1, description="页码")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="每页数量")] = 20,
) -> JSONResponse:
    """获取操作日志列表"""
    stmt = select(CommandLogModel)

    # 应用筛选条件
    if device_id:
        stmt = stmt.where(CommandLogModel.device_id == device_id)
    if user_id:
        stmt = stmt.where(CommandLogModel.user_id == user_id)
    if action:
        stmt = stmt.where(CommandLogModel.action == action)
    if status:
        stmt = stmt.where(CommandLogModel.status == status)
    if start_time:
        stmt = stmt.where(CommandLogModel.created_at >= start_time)
    if end_time:
        stmt = stmt.where(CommandLogModel.created_at <= end_time)

    # 计算总数
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await auth.db.execute(count_stmt)).scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    stmt = stmt.order_by(CommandLogModel.created_at.desc()).offset(offset).limit(page_size)
    logs = (await auth.db.execute(stmt)).scalars().all()

    items = [CommandLogResponse.model_validate(log) for log in logs]
    return SuccessResponse(
        data=CommandLogListResponse(items=items, total=total), msg="获取成功"
    )


@LogRouter.get(
    "/detail/{id}",
    summary="获取操作日志详情",
    description="获取操作日志详情",
    response_model=CommandLogResponse,
)
async def get_log(
    id: Annotated[int, Path(description="日志ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:log:detail"]))],
) -> JSONResponse:
    """获取操作日志详情"""
    stmt = select(CommandLogModel).where(CommandLogModel.id == id)
    log = (await auth.db.execute(stmt)).scalar_one_or_none()

    if not log:
        return ErrorResponse(msg="日志不存在")

    return SuccessResponse(data=CommandLogResponse.model_validate(log), msg="获取成功")
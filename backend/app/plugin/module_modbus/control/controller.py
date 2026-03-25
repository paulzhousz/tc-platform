"""
Modbus 设备管理 API 控制器
"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import ErrorResponse, SuccessResponse
from app.core.dependencies import AuthPermission
from app.core.logger import log
from app.core.router_class import OperationLogRoute
from app.plugin.module_modbus.control.services.connection_pool import connection_pool
from app.plugin.module_modbus.models import DeviceModel, TagPointModel
from app.plugin.module_modbus.schemas import (
    DeviceCreate,
    DeviceListResponse,
    DeviceResponse,
    DeviceUpdate,
    TagPointCreate,
    TagPointListResponse,
    TagPointResponse,
    TagPointUpdate,
)

DeviceRouter = APIRouter(
    route_class=OperationLogRoute, prefix="/device", tags=["Modbus设备管理"]
)


# ==================== 设备管理 API ====================


@DeviceRouter.get(
    "/list",
    summary="获取设备列表",
    description="获取所有设备列表",
    response_model=DeviceListResponse,
)
async def list_devices(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:device:query"]))],
) -> JSONResponse:
    """获取设备列表"""
    stmt = select(DeviceModel).order_by(DeviceModel.created_at.desc())
    devices = (await auth.db.execute(stmt)).scalars().all()

    items = [DeviceResponse.model_validate(d) for d in devices]
    return SuccessResponse(
        data=DeviceListResponse(items=items, total=len(items)),
        msg="获取设备列表成功",
    )


@DeviceRouter.post(
    "/create",
    summary="创建设备",
    description="创建新设备",
    response_model=DeviceResponse,
)
async def create_device(
    data: DeviceCreate,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:device:create"]))],
) -> JSONResponse:
    """创建设备"""
    # 检查编码是否已存在
    stmt = select(DeviceModel).where(DeviceModel.code == data.code)
    existing = (await auth.db.execute(stmt)).scalar_one_or_none()
    if existing:
        return ErrorResponse(msg=f"设备编码 '{data.code}' 已存在")

    device = DeviceModel(**data.model_dump())
    auth.db.add(device)
    await auth.db.commit()
    await auth.db.refresh(device)

    # 添加到连接池
    try:
        connection_pool.add_device(device)
    except Exception as e:
        log.warning(f"设备添加到连接池失败: {e}")

    log.info(f"创建设备成功: {device.name}")
    return SuccessResponse(data=DeviceResponse.model_validate(device), msg="创建设备成功")


@DeviceRouter.get(
    "/detail/{id}",
    summary="获取设备详情",
    description="获取设备详情",
    response_model=DeviceResponse,
)
async def get_device(
    id: Annotated[int, Path(description="设备ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:device:detail"]))],
) -> JSONResponse:
    """获取设备详情"""
    stmt = select(DeviceModel).where(DeviceModel.id == id)
    device = (await auth.db.execute(stmt)).scalar_one_or_none()
    if not device:
        return ErrorResponse(msg="设备不存在")

    return SuccessResponse(data=DeviceResponse.model_validate(device), msg="获取设备详情成功")


@DeviceRouter.put(
    "/update/{id}",
    summary="更新设备",
    description="更新设备信息",
    response_model=DeviceResponse,
)
async def update_device(
    id: Annotated[int, Path(description="设备ID")],
    data: DeviceUpdate,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:device:update"]))],
) -> JSONResponse:
    """更新设备"""
    stmt = select(DeviceModel).where(DeviceModel.id == id)
    device = (await auth.db.execute(stmt)).scalar_one_or_none()
    if not device:
        return ErrorResponse(msg="设备不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(device, key, value)

    await auth.db.commit()
    await auth.db.refresh(device)

    # 更新连接池
    connection_pool.remove_device(id)
    try:
        connection_pool.add_device(device)
    except Exception as e:
        log.warning(f"设备重新添加到连接池失败: {e}")

    log.info(f"更新设备成功: {device.name}")
    return SuccessResponse(data=DeviceResponse.model_validate(device), msg="更新设备成功")


@DeviceRouter.delete(
    "/delete",
    summary="删除设备",
    description="删除设备",
)
async def delete_device(
    ids: Annotated[list[int], Body(description="设备ID列表")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:device:delete"]))],
) -> JSONResponse:
    """删除设备"""
    for device_id in ids:
        stmt = select(DeviceModel).where(DeviceModel.id == device_id)
        device = (await auth.db.execute(stmt)).scalar_one_or_none()
        if device:
            # 从连接池移除
            connection_pool.remove_device(device_id)
            await auth.db.delete(device)

    await auth.db.commit()
    log.info(f"删除设备成功: {ids}")
    return SuccessResponse(msg="删除设备成功")


@DeviceRouter.post(
    "/{id}/test",
    summary="测试设备连接",
    description="测试设备连接是否正常",
)
async def test_device_connection(
    id: Annotated[int, Path(description="设备ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:device:detail"]))],
) -> JSONResponse:
    """测试设备连接"""
    stmt = select(DeviceModel).where(DeviceModel.id == id)
    device = (await auth.db.execute(stmt)).scalar_one_or_none()
    if not device:
        return ErrorResponse(msg="设备不存在")

    # 尝试获取连接
    client = connection_pool.acquire(id)
    if not client:
        return SuccessResponse(
            data={"connected": False, "message": "无法获取连接"},
            msg="连接测试失败",
        )

    try:
        # 尝试读取一个寄存器
        result = client.read_holding_registers(0, 1, slave=device.slave_id)
        if result.get("success"):
            return SuccessResponse(
                data={"connected": True, "message": "连接正常"},
                msg="连接测试成功",
            )
        else:
            return SuccessResponse(
                data={"connected": False, "message": result.get("error", "读取失败")},
                msg="连接测试失败",
            )
    except Exception as e:
        return SuccessResponse(
            data={"connected": False, "message": str(e)},
            msg="连接测试失败",
        )
    finally:
        connection_pool.release(id, client)


# ==================== 点位管理 API ====================


@DeviceRouter.get(
    "/{device_id}/tag/list",
    summary="获取点位列表",
    description="获取设备的点位列表",
    response_model=TagPointListResponse,
)
async def list_tags(
    device_id: Annotated[int, Path(description="设备ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:tag:query"]))],
) -> JSONResponse:
    """获取设备的点位列表"""
    stmt = (
        select(TagPointModel)
        .where(TagPointModel.device_id == device_id)
        .order_by(TagPointModel.sort_order, TagPointModel.id)
    )
    tags = (await auth.db.execute(stmt)).scalars().all()

    items = [TagPointResponse.model_validate(t) for t in tags]
    return SuccessResponse(
        data=TagPointListResponse(items=items, total=len(items)),
        msg="获取点位列表成功",
    )


@DeviceRouter.post(
    "/{device_id}/tag/create",
    summary="创建点位",
    description="创建新点位",
    response_model=TagPointResponse,
)
async def create_tag(
    device_id: Annotated[int, Path(description="设备ID")],
    data: TagPointCreate,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:tag:create"]))],
) -> JSONResponse:
    """创建点位"""
    # 检查设备是否存在
    stmt = select(DeviceModel).where(DeviceModel.id == device_id)
    device = (await auth.db.execute(stmt)).scalar_one_or_none()
    if not device:
        return ErrorResponse(msg="设备不存在")

    # 检查点位编码是否已存在
    stmt = select(TagPointModel).where(
        TagPointModel.device_id == device_id, TagPointModel.code == data.code
    )
    existing = (await auth.db.execute(stmt)).scalar_one_or_none()
    if existing:
        return ErrorResponse(msg=f"点位编码 '{data.code}' 已存在")

    tag = TagPointModel(**data.model_dump(), device_id=device_id)
    auth.db.add(tag)
    await auth.db.commit()
    await auth.db.refresh(tag)

    log.info(f"创建点位成功: {tag.name}")
    return SuccessResponse(data=TagPointResponse.model_validate(tag), msg="创建点位成功")


@DeviceRouter.put(
    "/tag/update/{tag_id}",
    summary="更新点位",
    description="更新点位信息",
    response_model=TagPointResponse,
)
async def update_tag(
    tag_id: Annotated[int, Path(description="点位ID")],
    data: TagPointUpdate,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:tag:update"]))],
) -> JSONResponse:
    """更新点位"""
    stmt = select(TagPointModel).where(TagPointModel.id == tag_id)
    tag = (await auth.db.execute(stmt)).scalar_one_or_none()
    if not tag:
        return ErrorResponse(msg="点位不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tag, key, value)

    await auth.db.commit()
    await auth.db.refresh(tag)

    log.info(f"更新点位成功: {tag.name}")
    return SuccessResponse(data=TagPointResponse.model_validate(tag), msg="更新点位成功")


@DeviceRouter.delete(
    "/tag/delete",
    summary="删除点位",
    description="删除点位",
)
async def delete_tag(
    ids: Annotated[list[int], Body(description="点位ID列表")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:tag:delete"]))],
) -> JSONResponse:
    """删除点位"""
    for tag_id in ids:
        stmt = select(TagPointModel).where(TagPointModel.id == tag_id)
        tag = (await auth.db.execute(stmt)).scalar_one_or_none()
        if tag:
            await auth.db.delete(tag)

    await auth.db.commit()
    log.info(f"删除点位成功: {ids}")
    return SuccessResponse(msg="删除点位成功")
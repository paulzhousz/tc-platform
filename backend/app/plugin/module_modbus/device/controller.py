"""
设备管理 Controller 层

遵循 FastAPI Admin 框架规范，使用 Annotated 类型提示和 AuthPermission 权限注入。
"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path
from fastapi.responses import JSONResponse

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.response import ErrorResponse, SuccessResponse
from app.core.dependencies import AuthPermission
from app.core.logger import log
from app.core.router_class import OperationLogRoute

from ..schemas import (
    DeviceCreate,
    DeviceListResponse,
    DeviceResponse,
    DeviceUpdate,
    TagPointCreate,
    TagPointListResponse,
    TagPointResponse,
    TagPointUpdate,
)
from .crud import DeviceCRUD
from .service import DeviceService, TagPointService

# ==================== 设备管理路由 ====================

DeviceRouter = APIRouter(
    route_class=OperationLogRoute, prefix="/device", tags=["Modbus设备管理"]
)


@DeviceRouter.get(
    "/list",
    summary="获取设备列表",
    description="获取所有设备列表",
    response_model=DeviceListResponse,
)
async def list_devices(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_modbus:device:query"]))],
    group: str | None = None,
    status: str | None = None,
) -> JSONResponse:
    """获取设备列表"""
    search = {}
    if group:
        search["group_name"] = group
    if status:
        search["device_status"] = status

    result = await DeviceService.list_service(auth=auth, search=search)
    return SuccessResponse(
        data=DeviceListResponse(items=result, total=len(result)),
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
    """创建设备

    注意：创建设备仅保存设备配置到数据库，不会自动建立连接。
    用户需要手动调用 /modbus/control/connect 接口连接设备。
    """
    result = await DeviceService.create_service(auth=auth, data=data)
    log.info(f"创建设备成功: {result['name']}")
    return SuccessResponse(data=result, msg="创建设备成功")


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
    result = await DeviceService.detail_service(auth=auth, id=id)
    return SuccessResponse(data=result, msg="获取设备详情成功")


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
    """更新设备

    注意：更新设备配置后，如果设备已在线，需要重新连接才能应用新配置。
    """
    from ..control.services.connection_pool import connection_pool

    result = await DeviceService.update_service(auth=auth, id=id, data=data)

    # 如果设备在连接池中，移除旧连接（用户需要手动重新连接）
    connection_pool.remove_device(id)

    log.info(f"更新设备成功: {result['name']}")
    return SuccessResponse(data=result, msg="更新设备成功")


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
    from ..control.services.connection_pool import connection_pool

    # 先从连接池移除
    for device_id in ids:
        connection_pool.remove_device(device_id)

    await DeviceService.delete_service(auth=auth, ids=ids)
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
    from ..control.services.connection_pool import connection_pool

    device = await DeviceCRUD(auth).get_by_id_crud(id=id)
    if not device:
        return ErrorResponse(msg="设备不存在")

    client = connection_pool.acquire(id)
    if not client:
        return SuccessResponse(
            data={"connected": False, "message": "无法获取连接"},
            msg="连接测试失败",
        )

    try:
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


# ==================== 点位管理 ====================


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
    result = await TagPointService.list_by_device_service(auth=auth, device_id=device_id)
    return SuccessResponse(
        data=TagPointListResponse(items=result, total=len(result)),
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
    result = await TagPointService.create_service(
        auth=auth, device_id=device_id, data=data
    )
    log.info(f"创建点位成功: {result['name']}")
    return SuccessResponse(data=result, msg="创建点位成功")


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
    result = await TagPointService.update_service(auth=auth, id=tag_id, data=data)
    log.info(f"更新点位成功: {result['name']}")
    return SuccessResponse(data=result, msg="更新点位成功")


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
    await TagPointService.delete_service(auth=auth, ids=ids)
    log.info(f"删除点位成功: {ids}")
    return SuccessResponse(msg="删除点位成功")

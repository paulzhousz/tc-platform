from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path
from fastapi.responses import JSONResponse

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.request import PaginationService
from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_params import PaginationQueryParam
from app.core.dependencies import AuthPermission
from app.core.logger import log
from app.core.router_class import OperationLogRoute

from .schema import (
    WorkflowNodeTypeCreateSchema,
    WorkflowNodeTypeOutSchema,
    WorkflowNodeTypeQueryParam,
    WorkflowNodeTypeUpdateSchema,
)
from .service import WorkflowNodeTypeService

WorkflowNodeTypeRouter = APIRouter(
    route_class=OperationLogRoute,
    prefix="/workflow/node-type",
    tags=["工作流编排节点类型"],
)


@WorkflowNodeTypeRouter.get(
    "/options",
    summary="编排节点类型选项",
    description="供 Vue Flow 画布左侧拖拽使用（与定时任务 task_node 无关）",
    response_model=ResponseSchema[list[dict]],
)
async def get_workflow_node_type_options_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_task:workflow:node-type:query"]))],
) -> JSONResponse:
    result = await WorkflowNodeTypeService.get_options_service(auth=auth)
    log.info("获取编排节点类型选项成功")
    return SuccessResponse(data=result, msg="获取编排节点类型选项成功")


@WorkflowNodeTypeRouter.get(
    "/detail/{id}",
    summary="编排节点类型详情",
    response_model=ResponseSchema[WorkflowNodeTypeOutSchema],
)
async def get_workflow_node_type_detail_controller(
    id: Annotated[int, Path(description="ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_task:workflow:node-type:query"]))],
) -> JSONResponse:
    result_dict = await WorkflowNodeTypeService.get_detail_service(auth=auth, id=id)
    log.info(f"获取编排节点类型详情成功 {id}")
    return SuccessResponse(data=result_dict, msg="获取编排节点类型详情成功")


@WorkflowNodeTypeRouter.get(
    "/list",
    summary="编排节点类型列表",
    response_model=ResponseSchema[list[WorkflowNodeTypeOutSchema]],
)
async def get_workflow_node_type_list_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[WorkflowNodeTypeQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_task:workflow:node-type:query"]))],
) -> JSONResponse:
    result_dict_list = await WorkflowNodeTypeService.get_list_service(
        auth=auth, search=search, order_by=page.order_by
    )
    result_dict = await PaginationService.paginate(
        data_list=result_dict_list,
        page_no=page.page_no,
        page_size=page.page_size,
    )
    log.info("查询编排节点类型列表成功")
    return SuccessResponse(data=result_dict, msg="查询编排节点类型列表成功")


@WorkflowNodeTypeRouter.post(
    "/create",
    summary="创建编排节点类型",
    response_model=ResponseSchema[WorkflowNodeTypeOutSchema],
)
async def create_workflow_node_type_controller(
    data: WorkflowNodeTypeCreateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_task:workflow:node-type:create"]))],
) -> JSONResponse:
    result_dict = await WorkflowNodeTypeService.create_service(auth=auth, data=data)
    log.info("创建编排节点类型成功")
    return SuccessResponse(data=result_dict, msg="创建编排节点类型成功")


@WorkflowNodeTypeRouter.put(
    "/update/{id}",
    summary="更新编排节点类型",
    response_model=ResponseSchema[WorkflowNodeTypeOutSchema],
)
async def update_workflow_node_type_controller(
    id: Annotated[int, Path(description="ID")],
    data: WorkflowNodeTypeUpdateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_task:workflow:node-type:update"]))],
) -> JSONResponse:
    result_dict = await WorkflowNodeTypeService.update_service(auth=auth, id=id, data=data)
    log.info(f"更新编排节点类型成功 {id}")
    return SuccessResponse(data=result_dict, msg="更新编排节点类型成功")


@WorkflowNodeTypeRouter.delete(
    "/delete",
    summary="删除编排节点类型",
    response_model=ResponseSchema[None],
)
async def delete_workflow_node_type_controller(
    ids: Annotated[list[int], Body(description="ID列表")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_task:workflow:node-type:delete"]))],
) -> JSONResponse:
    await WorkflowNodeTypeService.delete_service(auth=auth, ids=ids)
    log.info(f"删除编排节点类型成功 {ids}")
    return SuccessResponse(msg="删除编排节点类型成功")

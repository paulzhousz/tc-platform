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
    WorkflowCreateSchema,
    WorkflowExecuteSchema,
    WorkflowOutSchema,
    WorkflowPublishSchema,
    WorkflowQueryParam,
    WorkflowUpdateSchema,
)
from .service import WorkflowService

WorkflowRouter = APIRouter(route_class=OperationLogRoute, prefix="/workflow/definition", tags=["工作流"])


@WorkflowRouter.get(
    "/detail/{id}",
    summary="工作流详情",
    description="根据ID获取工作流详情（含画布 nodes/edges）",
    response_model=ResponseSchema[WorkflowOutSchema],
)
async def get_workflow_detail_controller(
    id: Annotated[int, Path(description="工作流ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_task:workflow:definition:detail"]))],
) -> JSONResponse:
    result_dict = await WorkflowService.get_workflow_detail_service(auth=auth, id=id)
    log.info(f"获取工作流详情成功 {id}")
    return SuccessResponse(data=result_dict, msg="获取工作流详情成功")


@WorkflowRouter.get(
    "/list",
    summary="工作流列表",
    description="分页查询工作流列表",
    response_model=ResponseSchema[list[WorkflowOutSchema]],
)
async def get_workflow_list_controller(
    page: Annotated[PaginationQueryParam, Depends()],
    search: Annotated[WorkflowQueryParam, Depends()],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_task:workflow:definition:query"]))],
) -> JSONResponse:
    result_dict_list = await WorkflowService.get_workflow_list_service(
        auth=auth, search=search, order_by=page.order_by
    )
    result_dict = await PaginationService.paginate(
        data_list=result_dict_list,
        page_no=page.page_no,
        page_size=page.page_size,
    )
    log.info("查询工作流列表成功")
    return SuccessResponse(data=result_dict, msg="查询工作流列表成功")


@WorkflowRouter.post(
    "/create",
    summary="创建工作流",
    description="创建草稿工作流，保存 Vue Flow 画布",
    response_model=ResponseSchema[WorkflowOutSchema],
)
async def create_workflow_controller(
    data: WorkflowCreateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_task:workflow:definition:create"]))],
) -> JSONResponse:
    result_dict = await WorkflowService.create_workflow_service(auth=auth, data=data)
    log.info("创建工作流成功")
    return SuccessResponse(data=result_dict, msg="创建工作流成功")


@WorkflowRouter.put(
    "/update/{id}",
    summary="更新工作流",
    description="更新工作流及画布",
    response_model=ResponseSchema[WorkflowOutSchema],
)
async def update_workflow_controller(
    id: Annotated[int, Path(description="工作流ID")],
    data: WorkflowUpdateSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_task:workflow:definition:update"]))],
) -> JSONResponse:
    result_dict = await WorkflowService.update_workflow_service(auth=auth, id=id, data=data)
    log.info(f"更新工作流成功 {id}")
    return SuccessResponse(data=result_dict, msg="更新工作流成功")


@WorkflowRouter.delete(
    "/delete",
    summary="删除工作流",
    description="批量删除工作流",
    response_model=ResponseSchema[None],
)
async def delete_workflow_controller(
    ids: Annotated[list[int], Body(description="ID列表")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_task:workflow:definition:delete"]))],
) -> JSONResponse:
    await WorkflowService.delete_workflow_service(auth=auth, ids=ids)
    log.info(f"删除工作流成功 {ids}")
    return SuccessResponse(msg="删除工作流成功")


@WorkflowRouter.post(
    "/publish/{id}",
    summary="发布工作流",
    description="校验 DAG 无环后标记为已发布，方可执行",
    response_model=ResponseSchema[WorkflowOutSchema],
)
async def publish_workflow_controller(
    id: Annotated[int, Path(description="工作流ID")],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_task:workflow:definition:update"]))],
    body: Annotated[WorkflowPublishSchema | None, Body()] = None,
) -> JSONResponse:
    result_dict = await WorkflowService.publish_workflow_service(auth=auth, id=id, body=body)
    log.info(f"发布工作流成功 {id}")
    return SuccessResponse(data=result_dict, msg="发布工作流成功")


@WorkflowRouter.post(
    "/execute",
    summary="执行工作流",
    description="使用 Prefect 按拓扑顺序执行已发布工作流",
    response_model=ResponseSchema[dict],
)
async def execute_workflow_controller(
    body: WorkflowExecuteSchema,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_task:workflow:definition:execute"]))],
) -> JSONResponse:
    result_dict = await WorkflowService.execute_workflow_service(auth=auth, body=body)
    log.info(f"执行工作流完成 workflow_id={body.workflow_id}")
    return SuccessResponse(data=result_dict, msg="执行工作流完成")

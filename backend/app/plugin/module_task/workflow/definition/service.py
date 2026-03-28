import asyncio
from typing import Any

from app.api.v1.module_system.auth.schema import AuthSchema
from app.core.exceptions import CustomException

from ..engine.prefect_engine import run_prefect_workflow_sync, utc_now_iso, validate_workflow_graph
from ..node_type.crud import WorkflowNodeTypeCRUD
from .crud import WorkflowCRUD
from .schema import (
    WorkflowCreateSchema,
    WorkflowExecuteResultSchema,
    WorkflowExecuteSchema,
    WorkflowOutSchema,
    WorkflowPublishSchema,
    WorkflowQueryParam,
    WorkflowUpdateSchema,
)


class WorkflowService:
    """工作流：画布存储 + 发布校验 + Prefect 执行"""

    @staticmethod
    def _out(obj: Any) -> dict:
        return WorkflowOutSchema.model_validate(obj).model_dump(mode="json")

    @classmethod
    async def get_workflow_detail_service(cls, auth: AuthSchema, id: int) -> dict:
        obj = await WorkflowCRUD(auth).get_obj_by_id_crud(id=id)
        if not obj:
            raise CustomException(msg="工作流不存在")
        return cls._out(obj)

    @classmethod
    async def get_workflow_list_service(
        cls,
        auth: AuthSchema,
        search: WorkflowQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> list[dict]:
        if order_by is None:
            order_by = [{"updated_time": "desc"}]
        obj_list = await WorkflowCRUD(auth).get_obj_list_crud(
            search=search.__dict__ if search else None,
            order_by=order_by,
        )
        return [cls._out(o) for o in obj_list]

    @classmethod
    async def create_workflow_service(cls, auth: AuthSchema, data: WorkflowCreateSchema) -> dict:
        exist = await WorkflowCRUD(auth).get(code=data.code)
        if exist:
            raise CustomException(msg="流程编码已存在")
        obj = await WorkflowCRUD(auth).create_obj_crud(data=data)
        if not obj:
            raise CustomException(msg="创建工作流失败")
        return cls._out(obj)

    @classmethod
    async def update_workflow_service(
        cls, auth: AuthSchema, id: int, data: WorkflowUpdateSchema
    ) -> dict:
        exist = await WorkflowCRUD(auth).get_obj_by_id_crud(id=id)
        if not exist:
            raise CustomException(msg="工作流不存在")
        if exist.code != data.code:
            other = await WorkflowCRUD(auth).get(code=data.code)
            if other:
                raise CustomException(msg="流程编码已存在")
        obj = await WorkflowCRUD(auth).update_obj_crud(id=id, data=data)
        if not obj:
            raise CustomException(msg="更新工作流失败")
        return cls._out(obj)

    @classmethod
    async def delete_workflow_service(cls, auth: AuthSchema, ids: list[int]) -> None:
        if not ids:
            raise CustomException(msg="删除ID不能为空")
        await WorkflowCRUD(auth).delete_obj_crud(ids=ids)

    @classmethod
    async def publish_workflow_service(
        cls, auth: AuthSchema, id: int, body: WorkflowPublishSchema | None = None
    ) -> dict:
        obj = await WorkflowCRUD(auth).get_obj_by_id_crud(id=id)
        if not obj:
            raise CustomException(msg="工作流不存在")
        nodes = obj.nodes or []
        edges = obj.edges or []

        try:
            validate_workflow_graph(nodes, edges)
        except ValueError as e:
            raise CustomException(msg=str(e)) from e

        data = WorkflowUpdateSchema(
            name=obj.name,
            code=obj.code,
            description=obj.description,
            nodes=obj.nodes,
            edges=obj.edges,
            workflow_status="published",
        )
        updated = await WorkflowCRUD(auth).update_obj_crud(id=id, data=data)
        if not updated:
            raise CustomException(msg="发布失败")
        return cls._out(updated)

    @classmethod
    async def execute_workflow_service(
        cls, auth: AuthSchema, body: WorkflowExecuteSchema
    ) -> dict:
        obj = await WorkflowCRUD(auth).get_obj_by_id_crud(id=body.workflow_id)
        if not obj:
            raise CustomException(msg="工作流不存在")
        if obj.workflow_status != "published":
            raise CustomException(msg="仅已发布的工作流可执行")

        nodes = obj.nodes or []
        edges = obj.edges or []
        if not nodes:
            raise CustomException(msg="工作流没有节点")

        codes = {n.get("type") for n in nodes if n.get("type")}
        templates: dict[str, dict[str, Any]] = {}
        for code in codes:
            node_type = await WorkflowNodeTypeCRUD(auth).get(code=code)
            if not node_type:
                raise CustomException(msg=f"编排节点类型未注册（请在「工作流编排节点类型」中维护，非定时任务节点）: {code}")
            if not node_type.func or not str(node_type.func).strip():
                raise CustomException(msg=f"编排节点类型未配置 func 代码块: {code}")
            templates[code] = {
                "func": node_type.func,
                "args": node_type.args,
                "kwargs": node_type.kwargs,
            }

        variables = body.variables or {}
        start = utc_now_iso()
        try:
            raw = await asyncio.to_thread(
                run_prefect_workflow_sync,
                nodes,
                edges,
                templates,
                variables,
            )
        except ValueError as e:
            raise CustomException(msg=str(e)) from e
        except CustomException:
            raise
        except Exception as e:
            end = utc_now_iso()
            err = WorkflowExecuteResultSchema(
                workflow_id=obj.id,
                workflow_name=obj.name,
                status="failed",
                start_time=start,
                end_time=end,
                variables=variables,
                node_results=None,
                error=str(e),
            )
            return err.model_dump(mode="json")

        end = utc_now_iso()
        ok = WorkflowExecuteResultSchema(
            workflow_id=obj.id,
            workflow_name=obj.name,
            status="completed",
            start_time=start,
            end_time=end,
            variables=variables,
            node_results=raw.get("node_results"),
            error=None,
        )
        return ok.model_dump(mode="json")

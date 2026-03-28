from app.api.v1.module_system.auth.schema import AuthSchema
from app.core.exceptions import CustomException

from .crud import WorkflowNodeTypeCRUD
from .schema import (
    WorkflowNodeTypeCreateSchema,
    WorkflowNodeTypeOutSchema,
    WorkflowNodeTypeQueryParam,
    WorkflowNodeTypeUpdateSchema,
)


class WorkflowNodeTypeService:
    """工作流编排节点类型（与定时任务 task_node 无关）"""

    @classmethod
    def _out(cls, obj) -> dict:
        return WorkflowNodeTypeOutSchema.model_validate(obj).model_dump(mode="json")

    @classmethod
    async def get_options_service(cls, auth: AuthSchema) -> list[dict]:
        """画布左侧 palette：仅返回启用项，结构与前端原 Node options 对齐"""
        objs = await WorkflowNodeTypeCRUD(auth).list_active_options_crud()
        return [
            {
                "id": o.id,
                "code": o.code,
                "name": o.name,
                "category": o.category,
                "args": o.args or "",
                "kwargs": o.kwargs or "{}",
            }
            for o in objs
        ]

    @classmethod
    async def get_detail_service(cls, auth: AuthSchema, id: int) -> dict:
        obj = await WorkflowNodeTypeCRUD(auth).get_obj_by_id_crud(id=id)
        if not obj:
            raise CustomException(msg="编排节点类型不存在")
        return cls._out(obj)

    @classmethod
    async def get_list_service(
        cls,
        auth: AuthSchema,
        search: WorkflowNodeTypeQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> list[dict]:
        if order_by is None:
            order_by = [{"sort_order": "asc"}, {"id": "asc"}]
        obj_list = await WorkflowNodeTypeCRUD(auth).get_obj_list_crud(
            search=search.__dict__ if search else None,
            order_by=order_by,
        )
        return [cls._out(o) for o in obj_list]

    @classmethod
    async def create_service(cls, auth: AuthSchema, data: WorkflowNodeTypeCreateSchema) -> dict:
        exist = await WorkflowNodeTypeCRUD(auth).get(code=data.code)
        if exist:
            raise CustomException(msg="节点编码已存在")
        obj = await WorkflowNodeTypeCRUD(auth).create_obj_crud(data=data)
        if not obj:
            raise CustomException(msg="创建失败")
        return cls._out(obj)

    @classmethod
    async def update_service(cls, auth: AuthSchema, id: int, data: WorkflowNodeTypeUpdateSchema) -> dict:
        exist = await WorkflowNodeTypeCRUD(auth).get_obj_by_id_crud(id=id)
        if not exist:
            raise CustomException(msg="编排节点类型不存在")
        if exist.code != data.code:
            other = await WorkflowNodeTypeCRUD(auth).get(code=data.code)
            if other:
                raise CustomException(msg="节点编码已存在")
        obj = await WorkflowNodeTypeCRUD(auth).update_obj_crud(id=id, data=data)
        if not obj:
            raise CustomException(msg="更新失败")
        return cls._out(obj)

    @classmethod
    async def delete_service(cls, auth: AuthSchema, ids: list[int]) -> None:
        if not ids:
            raise CustomException(msg="删除ID不能为空")
        await WorkflowNodeTypeCRUD(auth).delete_obj_crud(ids=ids)

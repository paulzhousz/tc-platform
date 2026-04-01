from collections.abc import Sequence
from typing import Any

from app.api.v1.module_system.auth.schema import AuthSchema
from app.common.enums import QueueEnum
from app.core.base_crud import CRUDBase

from .model import WorkflowNodeTypeModel
from .schema import WorkflowNodeTypeCreateSchema, WorkflowNodeTypeUpdateSchema


class WorkflowNodeTypeCRUD(CRUDBase[WorkflowNodeTypeModel, WorkflowNodeTypeCreateSchema, WorkflowNodeTypeUpdateSchema]):
    """编排节点类型 CRUD"""

    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        super().__init__(model=WorkflowNodeTypeModel, auth=auth)

    async def get_obj_by_id_crud(
        self, id: int, preload: list[str | Any] | None = None
    ) -> WorkflowNodeTypeModel | None:
        return await self.get(id=id, preload=preload)

    async def get_obj_list_crud(
        self,
        search: dict | None = None,
        order_by: list[dict[str, str]] | None = None,
        preload: list[str | Any] | None = None,
    ) -> Sequence[WorkflowNodeTypeModel]:
        return await self.list(search=search, order_by=order_by, preload=preload)

    async def create_obj_crud(self, data: WorkflowNodeTypeCreateSchema) -> WorkflowNodeTypeModel | None:
        return await self.create(data=data)

    async def update_obj_crud(self, id: int, data: WorkflowNodeTypeUpdateSchema) -> WorkflowNodeTypeModel | None:
        return await self.update(id=id, data=data)

    async def delete_obj_crud(self, ids: list[int]) -> None:
        await self.delete(ids=ids)

    async def list_active_options_crud(self) -> Sequence[WorkflowNodeTypeModel]:
        """画布：仅启用的类型，按 sort_order、id 排序"""
        return await self.get_obj_list_crud(
            search={"is_active": (QueueEnum.eq.value, True)},
            order_by=[{"sort_order": "asc"}, {"id": "asc"}],
        )

from collections.abc import Sequence
from typing import Any

from app.api.v1.module_system.auth.schema import AuthSchema
from app.core.base_crud import CRUDBase

from .model import WorkflowModel
from .schema import WorkflowCreateSchema, WorkflowUpdateSchema


class WorkflowCRUD(CRUDBase[WorkflowModel, WorkflowCreateSchema, WorkflowUpdateSchema]):
    """工作流数据层"""

    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        super().__init__(model=WorkflowModel, auth=auth)

    async def get_obj_by_id_crud(
        self, id: int, preload: list[str | Any] | None = None
    ) -> WorkflowModel | None:
        return await self.get(id=id, preload=preload)

    async def get_obj_list_crud(
        self,
        search: dict | None = None,
        order_by: list[dict[str, str]] | None = None,
        preload: list[str | Any] | None = None,
    ) -> Sequence[WorkflowModel]:
        return await self.list(search=search, order_by=order_by, preload=preload)

    async def create_obj_crud(self, data: WorkflowCreateSchema) -> WorkflowModel | None:
        return await self.create(data=data)

    async def update_obj_crud(self, id: int, data: WorkflowUpdateSchema) -> WorkflowModel | None:
        return await self.update(id=id, data=data)

    async def delete_obj_crud(self, ids: list[int]) -> None:
        await self.delete(ids=ids)

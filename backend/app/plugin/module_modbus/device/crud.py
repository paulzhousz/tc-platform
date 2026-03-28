"""
设备管理 CRUD 层

遵循 FastAPI Admin 框架规范，继承 CRUDBase 基类。
"""

from collections.abc import Sequence
from typing import Any

from app.api.v1.module_system.auth.schema import AuthSchema
from app.core.base_crud import CRUDBase

from ..models import DeviceModel, TagPointModel
from ..schemas import DeviceCreate, DeviceUpdate, TagPointCreate, TagPointUpdate


class DeviceCRUD(CRUDBase[DeviceModel, DeviceCreate, DeviceUpdate]):
    """设备数据访问层"""

    def __init__(self, auth: AuthSchema) -> None:
        """
        初始化设备 CRUD

        参数:
        - auth (AuthSchema): 认证信息模型
        """
        super().__init__(model=DeviceModel, auth=auth)

    async def get_by_id_crud(
        self, id: int, preload: list[str | Any] | None = None
    ) -> DeviceModel | None:
        """获取设备详情"""
        return await self.get(id=id, preload=preload)

    async def get_by_code_crud(self, code: str) -> DeviceModel | None:
        """根据编码获取设备"""
        return await self.get(code=code)

    async def list_crud(
        self,
        search: dict | None = None,
        order_by: list[dict[str, str]] | None = None,
        preload: list[str | Any] | None = None,
    ) -> Sequence[DeviceModel]:
        """获取设备列表"""
        return await self.list(search=search, order_by=order_by, preload=preload)

    async def page_crud(
        self,
        offset: int,
        limit: int,
        order_by: list[dict[str, str]] | None = None,
        search: dict | None = None,
        preload: list[str | Any] | None = None,
    ) -> dict:
        """分页查询设备"""
        from ..schemas import DeviceResponse

        order_by_list = order_by or [{"id": "desc"}]
        search_dict = search or {}

        return await self.page(
            offset=offset,
            limit=limit,
            order_by=order_by_list,
            search=search_dict,
            out_schema=DeviceResponse,
            preload=preload,
        )

    async def create_crud(self, data: DeviceCreate) -> DeviceModel | None:
        """创建设备"""
        return await self.create(data=data)

    async def update_crud(self, id: int, data: DeviceUpdate) -> DeviceModel | None:
        """更新设备"""
        return await self.update(id=id, data=data)

    async def delete_crud(self, ids: list[int]) -> None:
        """批量删除设备"""
        return await self.delete(ids=ids)


class TagPointCRUD(CRUDBase[TagPointModel, TagPointCreate, TagPointUpdate]):
    """点位数据访问层"""

    def __init__(self, auth: AuthSchema) -> None:
        """
        初始化点位 CRUD

        参数:
        - auth (AuthSchema): 认证信息模型
        """
        super().__init__(model=TagPointModel, auth=auth)

    async def get_by_id_crud(
        self, id: int, preload: list[str | Any] | None = None
    ) -> TagPointModel | None:
        """获取点位详情"""
        return await self.get(id=id, preload=preload)

    async def get_by_code_crud(
        self, device_id: int, code: str
    ) -> TagPointModel | None:
        """根据设备ID和编码获取点位"""
        return await self.get(device_id=device_id, code=code)

    async def list_by_device_crud(
        self,
        device_id: int,
        search: dict | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> Sequence[TagPointModel]:
        """获取设备的点位列表"""
        search_dict = {"device_id": device_id}
        if search:
            search_dict.update(search)
        return await self.list(search=search_dict, order_by=order_by)

    async def create_crud(
        self, device_id: int, data: TagPointCreate
    ) -> TagPointModel | None:
        """创建点位"""
        # 添加 device_id 到数据中
        obj_dict = data.model_dump()
        obj_dict["device_id"] = device_id
        return await self.create(data=obj_dict)

    async def update_crud(self, id: int, data: TagPointUpdate) -> TagPointModel | None:
        """更新点位"""
        return await self.update(id=id, data=data)

    async def delete_crud(self, ids: list[int]) -> None:
        """批量删除点位"""
        return await self.delete(ids=ids)

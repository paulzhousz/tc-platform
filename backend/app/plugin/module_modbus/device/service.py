"""
设备管理 Service 层

遵循 FastAPI Admin 框架规范，使用 @classmethod，第一个参数为 auth: AuthSchema。
"""

from app.api.v1.module_system.auth.schema import AuthSchema
from app.core.exceptions import CustomException

from ..schemas import (
    DeviceCreate,
    DeviceResponse,
    DeviceUpdate,
    TagPointCreate,
    TagPointResponse,
    TagPointUpdate,
)
from .crud import DeviceCRUD, TagPointCRUD


class DeviceService:
    """设备管理业务逻辑层"""

    @classmethod
    async def detail_service(cls, auth: AuthSchema, id: int) -> dict:
        """获取设备详情"""
        obj = await DeviceCRUD(auth).get_by_id_crud(id=id)
        if not obj:
            raise CustomException(msg="设备不存在")
        return DeviceResponse.model_validate(obj).model_dump()

    @classmethod
    async def list_service(
        cls,
        auth: AuthSchema,
        search: dict | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> list[dict]:
        """获取设备列表"""
        order_by_list = order_by or [{"id": "desc"}]
        obj_list = await DeviceCRUD(auth).list_crud(search=search, order_by=order_by_list)
        return [DeviceResponse.model_validate(obj).model_dump() for obj in obj_list]

    @classmethod
    async def page_service(
        cls,
        auth: AuthSchema,
        page_no: int,
        page_size: int,
        search: dict | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> dict:
        """分页查询设备"""
        order_by_list = order_by or [{"id": "desc"}]
        offset = (page_no - 1) * page_size

        result = await DeviceCRUD(auth).page_crud(
            offset=offset,
            limit=page_size,
            order_by=order_by_list,
            search=search,
        )
        return result

    @classmethod
    async def create_service(cls, auth: AuthSchema, data: DeviceCreate) -> dict:
        """创建设备"""
        # 检查编码是否重复
        obj = await DeviceCRUD(auth).get_by_code_crud(code=data.code)
        if obj:
            raise CustomException(msg=f"设备编码 '{data.code}' 已存在")

        # 创建设备，默认状态为 offline
        obj_dict = data.model_dump()
        obj_dict["device_status"] = "offline"
        obj = await DeviceCRUD(auth).create(data=obj_dict)
        return DeviceResponse.model_validate(obj).model_dump()

    @classmethod
    async def update_service(cls, auth: AuthSchema, id: int, data: DeviceUpdate) -> dict:
        """更新设备"""
        obj = await DeviceCRUD(auth).get_by_id_crud(id=id)
        if not obj:
            raise CustomException(msg="设备不存在")

        obj = await DeviceCRUD(auth).update_crud(id=id, data=data)
        return DeviceResponse.model_validate(obj).model_dump()

    @classmethod
    async def delete_service(cls, auth: AuthSchema, ids: list[int]) -> None:
        """删除设备"""
        if len(ids) < 1:
            raise CustomException(msg="删除对象不能为空")

        for id in ids:
            obj = await DeviceCRUD(auth).get_by_id_crud(id=id)
            if not obj:
                raise CustomException(msg=f"ID为{id}的设备不存在")

        await DeviceCRUD(auth).delete_crud(ids=ids)


class TagPointService:
    """点位管理业务逻辑层"""

    @classmethod
    async def detail_service(cls, auth: AuthSchema, id: int) -> dict:
        """获取点位详情"""
        obj = await TagPointCRUD(auth).get_by_id_crud(id=id)
        if not obj:
            raise CustomException(msg="点位不存在")
        return TagPointResponse.model_validate(obj).model_dump()

    @classmethod
    async def list_by_device_service(
        cls,
        auth: AuthSchema,
        device_id: int,
        search: dict | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> list[dict]:
        """获取设备的点位列表"""
        order_by_list = order_by or [{"sort_order": "asc"}, {"id": "asc"}]
        obj_list = await TagPointCRUD(auth).list_by_device_crud(
            device_id=device_id, search=search, order_by=order_by_list
        )
        return [TagPointResponse.model_validate(obj).model_dump() for obj in obj_list]

    @classmethod
    async def create_service(
        cls, auth: AuthSchema, device_id: int, data: TagPointCreate
    ) -> dict:
        """创建点位"""
        # 检查设备是否存在
        device = await DeviceCRUD(auth).get_by_id_crud(id=device_id)
        if not device:
            raise CustomException(msg="设备不存在")

        # 检查点位编码是否重复
        obj = await TagPointCRUD(auth).get_by_code_crud(
            device_id=device_id, code=data.code
        )
        if obj:
            raise CustomException(msg=f"点位编码 '{data.code}' 已存在")

        obj = await TagPointCRUD(auth).create_crud(device_id=device_id, data=data)
        return TagPointResponse.model_validate(obj).model_dump()

    @classmethod
    async def update_service(
        cls, auth: AuthSchema, id: int, data: TagPointUpdate
    ) -> dict:
        """更新点位"""
        obj = await TagPointCRUD(auth).get_by_id_crud(id=id)
        if not obj:
            raise CustomException(msg="点位不存在")

        obj = await TagPointCRUD(auth).update_crud(id=id, data=data)
        return TagPointResponse.model_validate(obj).model_dump()

    @classmethod
    async def delete_service(cls, auth: AuthSchema, ids: list[int]) -> None:
        """删除点位"""
        if len(ids) < 1:
            raise CustomException(msg="删除对象不能为空")

        for id in ids:
            obj = await TagPointCRUD(auth).get_by_id_crud(id=id)
            if not obj:
                raise CustomException(msg=f"ID为{id}的点位不存在")

        await TagPointCRUD(auth).delete_crud(ids=ids)

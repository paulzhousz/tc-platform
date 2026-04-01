import io
import os
import re
import zipfile
from collections.abc import Callable
from typing import Any

import anyio
import sqlglot
from sqlglot.expressions import (
    Add,
    Alter,
    Create,
    Delete,
    Drop,
    Insert,
    Table,
    TruncateTable,
    Update,
)

from app.api.v1.module_system.auth.schema import AuthSchema
from app.config.path_conf import BASE_DIR
from app.config.setting import settings
from app.core.exceptions import CustomException
from app.core.logger import log

from .crud import GenTableColumnCRUD, GenTableCRUD
from .schema import (
    GenTableColumnOutSchema,
    GenTableColumnSchema,
    GenTableOutSchema,
    GenTableQueryParam,
    GenTableSchema,
)
from .tools.gen_util import GenUtils
from .tools.jinja2_template_util import Jinja2TemplateUtil


def handle_service_exception(func: Callable) -> Callable:
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except CustomException:
            raise
        except Exception as e:
            raise CustomException(msg=f"{func.__name__}执行失败: {e!s}")

    return wrapper


_MENU_TYPE_CATALOG = 1  # 与 sys_menu.type、前端 MenuTypeEnum.CATALOG 一致
_MENU_TYPE_MENU = 2


class GenTableService:
    """代码生成业务表服务层"""

    @classmethod
    def _is_example_style(cls, package_name: str | None, module_name: str | None) -> bool:
        """委托 ``Jinja2TemplateUtil.is_example_style``，保证与模板/路径逻辑一致。"""
        return Jinja2TemplateUtil.is_example_style(package_name, module_name)

    @classmethod
    async def _assert_parent_menu_is_catalog(cls, auth: AuthSchema, parent_menu_id: int | None) -> None:
        """上级菜单仅允许目录：与前端树只展示目录一致，避免挂到菜单/按钮下。"""
        if parent_menu_id is None:
            return
        from app.api.v1.module_system.menu.crud import MenuCRUD

        m = await MenuCRUD(auth).get_by_id_crud(parent_menu_id)
        if not m:
            raise CustomException(msg="上级菜单不存在")
        if m.type != _MENU_TYPE_CATALOG:
            raise CustomException(msg="上级菜单须选择目录类型")

    @classmethod
    def _menu_route_first_segment(
        cls, parent_catalog_id: int | None, package_name: str, module_name: str | None
    ) -> str:
        """前端页面路由首段（与菜单 ``route_path`` 第一段一致）。

        - **有上级目录**：使用 ``package_name``（如 ``/gencode/业务``）。
        - **无上级**：使用 ``module_name``（如 ``module_gencode`` → ``/module_gencode/业务``），与侧栏第一层目录一致。

        说明：后端 HTTP API 仍由动态路由 ``module_xxx → /xxx`` 映射，与此前端路径可不同。
        """
        pn = (package_name or "").strip()
        mn = (module_name or "").strip()
        is_ex = cls._is_example_style(pn, mn)
        if parent_catalog_id is not None:
            if not pn:
                raise CustomException(msg="包名不能为空")
            return pn
        # 无上级：示例模式首段为插件包目录 module_xxx；旧模式首段为 module_xxx（原 module_name 字段）
        if is_ex:
            if not pn:
                raise CustomException(msg="包名不能为空")
            return pn if pn.startswith("module_") else f"module_{pn}"
        if mn:
            return mn
        if not pn:
            raise CustomException(msg="包名或模块名至少填写一项以生成路由")
        if pn.startswith("module_"):
            return pn
        return f"module_{pn}"

    @classmethod
    def _catalog_menu_dir_key(
        cls, parent_catalog_id: int | None, package_name: str, module_name: str | None
    ) -> str:
        """菜单上「模块目录」节点的 name（与路由第一段 package 独立）。

        - 有上级目录：``包名（不带 module_ 前缀）``，侧栏为 上级 → 短包名 → 功能菜单 → 按钮。
        - 无上级：``module_包名``，与 ``plugin/module_xxx`` 目录一致，侧栏为 module_包名 → 功能 → 按钮。
        """
        pn = (package_name or "").strip()
        mn = (module_name or "").strip()
        is_ex = cls._is_example_style(pn, mn)
        if parent_catalog_id is not None:
            if not pn:
                raise CustomException(msg="包名不能为空")
            base = pn[len("module_") :] if pn.startswith("module_") else pn
            # 示例模式：同一包下多模块须区分目录节点，避免 name 都为短包名导致串单
            if is_ex and mn:
                return f"{base}_{mn}"
            if pn.startswith("module_"):
                return base
            return pn
        if is_ex:
            if not pn or not mn:
                raise CustomException(msg="包名、模块名不能为空")
            # 根侧栏：按「包+模块」唯一，避免多模块共用一个目录菜单
            return f"{pn}_{mn}"
        if mn:
            return mn
        if not pn:
            raise CustomException(msg="包名或模块名至少填写一项以生成菜单目录")
        if pn.startswith("module_"):
            return pn
        return f"module_{pn}"

    @classmethod
    async def _get_or_create_package_directory_menu(
        cls,
        menu_crud: Any,
        parent_catalog_id: int | None,
        package_name: str,
        module_name: str | None,
        business_name: str,
    ) -> int:
        """创建或复用 type=1 模块目录；固定为「目录 → 菜单 → 按钮」中的第一层目录。"""
        from app.api.v1.module_system.menu.schema import MenuCreateSchema
        from app.utils.common_util import CamelCaseUtil

        pn = (package_name or "").strip()
        if not pn:
            raise CustomException(msg="包名不能为空")
        mn = (module_name or "").strip()
        bn = (business_name or "").strip()
        is_ex = cls._is_example_style(pn, mn)
        dir_key = cls._catalog_menu_dir_key(parent_catalog_id, pn, module_name)

        if parent_catalog_id is not None:
            existing = await menu_crud.get(
                name=dir_key, type=_MENU_TYPE_CATALOG, parent_id=parent_catalog_id
            )
        else:
            existing = await menu_crud.get(
                name=dir_key, type=_MENU_TYPE_CATALOG, parent_id=("None", None)
            )
        if existing:
            log.info(
                f"代码生成：复用模块目录菜单 id={existing.id} name={dir_key!r} parent={parent_catalog_id!r}"
            )
            return int(existing.id)

        route_first = cls._menu_route_first_segment(parent_catalog_id, pn, module_name)
        # 示例模式：目录菜单对应「包/模块」路径；默认跳到模块根，避免多模块共用一个 redirect 指向某一业务
        if is_ex:
            catalog_route_path = f"/{route_first}/{mn}"
            redirect = f"/{route_first}/{mn}"
        else:
            catalog_route_path = f"/{route_first}"
            redirect = f"/{route_first}/{bn}" if bn else f"/{route_first}"
        created = await menu_crud.create(
            MenuCreateSchema(
                name=dir_key,
                type=_MENU_TYPE_CATALOG,
                order=9999,
                permission=None,
                icon="menu",
                route_name=CamelCaseUtil.snake_to_camel(route_first),
                route_path=catalog_route_path,
                component_path=None,
                redirect=redirect,
                hidden=False,
                keep_alive=True,
                always_show=False,
                title=dir_key,
                params=None,
                affix=False,
                parent_id=parent_catalog_id,
                status="0",
                description="模块目录（代码生成）",
            )
        )
        log.info(
            f"代码生成：新建模块目录菜单 id={created.id} name={dir_key!r} under_parent={parent_catalog_id!r}"
        )
        return int(created.id)

    @classmethod
    def normalize_and_validate_master_sub(cls, data: GenTableSchema) -> None:
        """主子表业务规则：两字段同填或同空；子表表名不得与主表相同。"""
        sn = data.sub_table_name
        fk = data.sub_table_fk_name
        if bool(sn) ^ bool(fk):
            raise CustomException(msg="子表表名与子表外键列须同时填写或同时留空")
        tn = (data.table_name or "").strip()
        if sn and fk and sn == tn:
            raise CustomException(msg="子表表名不能与主表表名相同")

    @classmethod
    @handle_service_exception
    async def get_gen_table_detail_service(cls, auth: AuthSchema, table_id: int) -> dict:
        """获取详细信息。

        参数:
        - auth (AuthSchema): 认证信息。
        - table_id (int): 业务表ID。

        返回:
        - dict: 包含业务表详细信息的字典。
        """
        gen_table = await cls.get_gen_table_by_id_service(auth, table_id)
        return gen_table.model_dump()

    @classmethod
    @handle_service_exception
    async def get_gen_table_list_service(
        cls, auth: AuthSchema, search: GenTableQueryParam
    ) -> list[dict]:
        """
        获取代码生成业务表列表信息。

        参数:
        - auth (AuthSchema): 认证信息。
        - search (GenTableQueryParam): 查询参数模型。

        返回:
        - list[dict]: 包含业务表列表信息的字典列表。
        """
        gen_table_list_result = await GenTableCRUD(auth=auth).get_gen_table_list(search)
        return [GenTableOutSchema.model_validate(obj).model_dump() for obj in gen_table_list_result]

    @classmethod
    @handle_service_exception
    async def get_gen_table_page_service(
        cls,
        auth: AuthSchema,
        page_no: int,
        page_size: int,
        search: GenTableQueryParam,
        order_by: list[dict[str, str]] | None = None,
    ) -> dict:
        """分页查询代码生成业务表（数据库 OFFSET/LIMIT）。"""
        offset = (page_no - 1) * page_size
        order = order_by or [{"created_time": "desc"}]
        return await GenTableCRUD(auth=auth).page(
            offset=offset,
            limit=page_size,
            order_by=order,
            search=search.__dict__,
            out_schema=GenTableOutSchema,
        )

    @classmethod
    @handle_service_exception
    async def get_gen_db_table_list_service(
        cls, auth: AuthSchema, search: GenTableQueryParam
    ) -> list[Any]:
        """获取数据库表列表。

        参数:
        - auth (AuthSchema): 认证信息。
        - search (GenTableQueryParam): 查询参数模型。

        返回:
        - list[Any]: 包含数据库表列表信息的任意类型列表。
        """
        gen_db_table_list_result = await GenTableCRUD(auth=auth).get_db_table_list(search)
        return gen_db_table_list_result

    @classmethod
    @handle_service_exception
    async def get_gen_db_table_list_by_name_service(
        cls, auth: AuthSchema, table_names: list[str]
    ) -> list[GenTableOutSchema]:
        """根据表名称组获取数据库表信息。

        参数:
        - auth (AuthSchema): 认证信息。
        - table_names (list[str]): 业务表名称列表。

        返回:
        - list[GenTableOutSchema]: 包含业务表详细信息的模型列表。
        """
        gen_db_table_list_result = await GenTableCRUD(auth).get_db_table_list_by_names(table_names)

        # 修复：将GenDBTableSchema对象转换为字典后再传递给GenTableOutSchema
        result = [
            GenTableOutSchema(**gen_table.model_dump()) for gen_table in gen_db_table_list_result
        ]

        return result

    @classmethod
    @handle_service_exception
    async def import_gen_table_service(
        cls, auth: AuthSchema, gen_table_list: list[GenTableOutSchema]
    ) -> bool:
        """导入表结构到生成器。

        参数:
        - auth (AuthSchema): 认证信息。
        - gen_table_list (list[GenTableOutSchema]): 包含业务表详细信息的模型列表。

        返回:
        - bool: 成功时返回True，失败时抛出异常。
        """
        # 检查是否有表需要导入
        if not gen_table_list:
            raise CustomException(msg="导入的表结构不能为空")
        try:
            for table in gen_table_list:
                _row = {
                    k: v
                    for k, v in table.model_dump().items()
                    if k in GenTableSchema.model_fields
                }
                cls.normalize_and_validate_master_sub(GenTableSchema.model_validate(_row))
                table_name = table.table_name
                # 检查表是否已存在
                existing_table = await GenTableCRUD(auth).get_gen_table_by_name(table_name)
                if existing_table:
                    raise CustomException(msg=f"以下表已存在，不能重复导入: {table_name}")
                GenUtils.init_table(table)
                if not table.columns:
                    table.columns = []
                add_gen_table = await GenTableCRUD(auth).add_gen_table(
                    GenTableSchema.model_validate(table.model_dump())
                )
                gen_table_columns = await GenTableColumnCRUD(auth).get_gen_db_table_columns_by_name(
                    table_name
                )
                if len(gen_table_columns) > 0:
                    table.id = add_gen_table.id
                    for column in gen_table_columns:
                        column_schema = GenTableColumnSchema(
                            table_id=table.id,
                            column_name=column.column_name,
                            column_comment=column.column_comment,
                            column_type=column.column_type,
                            column_length=column.column_length,
                            column_default=column.column_default,
                            is_pk=column.is_pk,
                            is_increment=column.is_increment,
                            is_nullable=column.is_nullable,
                            is_unique=column.is_unique,
                            sort=column.sort,
                            python_type=column.python_type,
                            python_field=column.python_field,
                        )
                        GenUtils.init_column_field(column_schema, table)
                        await GenTableColumnCRUD(auth).create_gen_table_column_crud(column_schema)
            return True
        except Exception as e:
            raise CustomException(msg=f"导入失败, {e!s}")

    @classmethod
    @handle_service_exception
    async def create_table_service(cls, auth: AuthSchema, sql: str) -> bool | None:
        """创建表结构并导入至代码生成模块。

        参数:
        - auth (AuthSchema): 认证信息。
        - sql (str): 包含`CREATE TABLE`语句的SQL字符串。

        返回:
        - bool | None: 成功时返回True，失败时抛出异常。
        """
        # 验证SQL非空
        if not sql or not sql.strip():
            raise CustomException(msg="SQL语句不能为空")
        try:
            # 解析SQL语句
            sql_statements = sqlglot.parse(sql, dialect=settings.DATABASE_TYPE)
            if not sql_statements:
                raise CustomException(msg="无法解析SQL语句，请检查SQL语法")

            # 校验sql语句是否为合法的建表语句
            validate_create = [
                isinstance(sql_statement, Create) for sql_statement in sql_statements
            ]
            validate_forbidden_keywords = [
                isinstance(
                    sql_statement,
                    (Add, Alter, Delete, Drop, Insert, TruncateTable, Update),
                )
                for sql_statement in sql_statements
            ]
            if not any(validate_create) or any(validate_forbidden_keywords):
                raise CustomException(msg="sql语句不是合法的建表语句")

            # 获取要创建的表名
            table_names = []
            for sql_statement in sql_statements:
                if isinstance(sql_statement, Create):
                    table = sql_statement.find(Table)
                    if table and table.name:
                        table_names.append(table.name)
            table_names = list(set(table_names))

            # 创建CRUD实例
            gen_table_crud = GenTableCRUD(auth=auth)

            # 检查每个表是否已存在
            for table_name in table_names:
                # 检查数据库中是否已存在该表
                if await gen_table_crud.check_table_exists(table_name):
                    raise CustomException(msg=f"表 {table_name} 已存在，请检查并修改表名后重试")

                # 检查代码生成模块中是否已导入该表
                existing_table = await gen_table_crud.get_gen_table_by_name(table_name)
                if existing_table:
                    raise CustomException(
                        msg=f"表 {table_name} 已在代码生成模块中存在，请检查并修改表名后重试"
                    )

            # 表不存在，执行SQL语句创建表
            for sql_statement in sql_statements:
                if not isinstance(sql_statement, Create):
                    continue
                exc_sql = sql_statement.sql(dialect=settings.DATABASE_TYPE)
                log.info(f"执行SQL语句: {exc_sql}")
                if not await gen_table_crud.execute_sql(exc_sql):
                    raise CustomException(msg=f"执行SQL语句 {exc_sql} 失败，请检查数据库")
            return True

        except Exception as e:
            raise CustomException(msg=f"创建表结构失败: {e!s}")

    @classmethod
    @handle_service_exception
    async def update_gen_table_service(
        cls, auth: AuthSchema, data: GenTableSchema, table_id: int
    ) -> dict[str, Any]:
        """编辑业务表信息。

        参数:
        - auth (AuthSchema): 认证信息。
        - data (GenTableSchema): 包含业务表详细信息的模型。
        - table_id (int): 业务表ID。

        返回:
        - dict[str, Any]: 更新后的业务表信息。
        """
        # 处理params为None的情况
        gen_table_info = await cls.get_gen_table_by_id_service(auth, table_id)
        if gen_table_info.id:
            try:
                cls.normalize_and_validate_master_sub(data)
                await cls._assert_parent_menu_is_catalog(auth, data.parent_menu_id)
                # 直接调用edit_gen_table方法，它会在内部处理排除嵌套字段的逻辑
                result = await GenTableCRUD(auth).edit_gen_table(table_id, data)
                if not result:
                    raise CustomException(msg="更新业务表信息失败")

                # 处理data.columns为None的情况
                if data.columns:
                    for gen_table_column in data.columns:
                        # 确保column有id字段
                        if hasattr(gen_table_column, "id") and gen_table_column.id:
                            column_schema = GenTableColumnSchema(**gen_table_column.model_dump())
                            await GenTableColumnCRUD(auth).update_gen_table_column_crud(
                                gen_table_column.id, column_schema
                            )
                # 重新获取带有预加载关系的对象，避免懒加载导致的MissingGreenlet错误
                updated_gen_table = await GenTableCRUD(auth).get_gen_table_by_id(table_id)
                out = GenTableOutSchema.model_validate(updated_gen_table)
                await cls.set_pk_column(out)
                await cls.hydrate_sub_table(auth, out)
                return out.model_dump()
            except CustomException:
                raise
            except Exception as e:
                raise CustomException(msg=str(e))
        else:
            raise CustomException(msg="业务表不存在")

    @classmethod
    @handle_service_exception
    async def delete_gen_table_service(cls, auth: AuthSchema, ids: list[int]) -> None:
        """删除业务表信息（先删字段，再删表）。

        参数:
        - auth (AuthSchema): 认证信息。
        - ids (list[int]): 业务表ID列表。

        返回:
        - None
        """
        # 验证ID列表非空
        if not ids:
            raise CustomException(msg="ID列表不能为空")

        try:
            # 先删除相关的字段信息
            await GenTableColumnCRUD(auth=auth).delete_gen_table_column_by_table_id_crud(ids)
            # 再删除表信息
            await GenTableCRUD(auth=auth).delete_gen_table(ids)
        except Exception as e:
            raise CustomException(msg=str(e))

    @classmethod
    @handle_service_exception
    async def get_gen_table_by_id_service(
        cls, auth: AuthSchema, table_id: int
    ) -> GenTableOutSchema:
        """获取需要生成代码的业务表详细信息。

        参数:
        - auth (AuthSchema): 认证信息。
        - table_id (int): 业务表ID。

        返回:
        - GenTableOutSchema: 业务表详细信息模型。
        """
        gen_table = await GenTableCRUD(auth=auth).get_gen_table_by_id(table_id)
        if not gen_table:
            raise CustomException(msg="业务表不存在")

        result = GenTableOutSchema.model_validate(gen_table)
        await cls.set_pk_column(result)
        await cls.hydrate_sub_table(auth, result)
        return result

    @classmethod
    @handle_service_exception
    async def get_gen_table_all_service(cls, auth: AuthSchema) -> list[GenTableOutSchema]:
        """获取所有业务表信息（列表）。

        参数:
        - auth (AuthSchema): 认证信息。

        返回:
        - list[GenTableOutSchema]: 业务表详细信息模型列表。
        """
        gen_table_all = await GenTableCRUD(auth=auth).get_gen_table_all() or []
        result = []
        for gen_table in gen_table_all:
            try:
                table_out = GenTableOutSchema.model_validate(gen_table)
                result.append(table_out)
            except Exception as e:
                log.error(f"转换业务表时出错: {e!s}")
                continue
        return result

    @classmethod
    @handle_service_exception
    async def preview_code_service(cls, auth: AuthSchema, table_id: int) -> dict[str, Any]:
        """
        预览代码（根据模板渲染内存结果）。

        参数:
        - auth (AuthSchema): 认证信息。
        - table_id (int): 业务表ID。

        返回:
        - dict[str, Any]: 文件名到渲染内容的映射。
        """
        raw = await GenTableCRUD(auth).get_gen_table_by_id(table_id)
        if not raw:
            raise CustomException(msg="业务表不存在")
        gen_table = GenTableOutSchema.model_validate(raw)
        await cls.set_pk_column(gen_table)
        await cls.hydrate_sub_table(auth, gen_table)
        cls._assert_master_sub_config_valid(gen_table)
        env = Jinja2TemplateUtil.get_env()
        context = Jinja2TemplateUtil.prepare_context(gen_table)
        template_list = Jinja2TemplateUtil.get_template_list()
        preview_code_result: dict[str, Any] = {}
        for template in template_list:
            try:
                render_content = await env.get_template(template).render_async(**context)
                out_key = Jinja2TemplateUtil.get_file_name(template, gen_table)
                preview_code_result[out_key] = render_content
            except Exception as e:
                log.error(f"渲染模板 {template} 时出错: {e!s}")
                out_key = Jinja2TemplateUtil.get_file_name(template, gen_table)
                preview_code_result[out_key] = f"渲染错误: {e!s}"
        if gen_table.sub and gen_table.sub_table:
            sub_ctx = Jinja2TemplateUtil.prepare_sub_render_context(gen_table, gen_table.sub_table)
            sub_table = gen_table.sub_table
            for template in template_list:
                try:
                    render_content = await env.get_template(template).render_async(**sub_ctx)
                    out_key = Jinja2TemplateUtil.get_file_name(template, sub_table)
                    preview_code_result[out_key] = render_content
                except Exception as e:
                    log.error(f"渲染子表模板 {template} 时出错: {e!s}")
                    out_key = Jinja2TemplateUtil.get_file_name(template, sub_table)
                    preview_code_result[out_key] = f"渲染错误: {e!s}"
        return preview_code_result

    @classmethod
    @handle_service_exception
    async def generate_code_service(cls, auth: AuthSchema, table_name: str) -> bool:
        """生成代码至指定路径（安全写入+可跳过覆盖）。

        菜单固定为 **目录(type=1) + 菜单(type=2) + 按钮(type=3)**：
        - **有上级目录**：``上级目录 / 包名(无 module_ 前缀) / 功能菜单 / 按钮``；页面路由 ``/包名/业务名``。
        - **无上级**：``module_包名 / 功能菜单 / 按钮``；页面路由 ``/module_包名/业务名``（与侧栏第一层一致）。
        - 后端 HTTP 接口仍为动态路由前缀 ``/短名``（``module_xxx``→``/xxx``），与前端页面路由可不同。

        参数:
        - auth (AuthSchema): 认证信息。
        - table_name (str): 业务表名。

        返回:
        - bool: 生成是否成功。
        """
        # 验证表名非空
        if not table_name or not table_name.strip():
            raise CustomException(msg="表名不能为空")
        env = Jinja2TemplateUtil.get_env()
        render_info = await cls.__get_gen_render_info(auth, table_name)
        gen_table_schema: GenTableOutSchema = render_info[3]

        from app.api.v1.module_system.menu.crud import MenuCRUD
        from app.api.v1.module_system.menu.schema import MenuCreateSchema
        from app.utils.common_util import CamelCaseUtil

        is_ex = cls._is_example_style(gen_table_schema.package_name, gen_table_schema.module_name)
        if is_ex:
            if not (gen_table_schema.module_name or "").strip():
                raise CustomException(msg="模块名称不能为空")
            pn = (gen_table_schema.package_name or "").strip()
            mn = (gen_table_schema.module_name or "").strip()
            raw_bn = (gen_table_schema.business_name or "").strip()
            perm_segs = [pn, mn]
            if raw_bn:
                perm_segs.extend(s for s in raw_bn.split("/") if s)
            permission_prefix = ":".join(perm_segs)
            _slug_src = raw_bn or mn
            _business_route_slug = Jinja2TemplateUtil.business_name_to_slug(_slug_src)
        else:
            if not gen_table_schema.business_name:
                raise CustomException(msg="业务名称不能为空")
            _bn_perm = (gen_table_schema.business_name or "").strip().replace("/", ":")
            permission_prefix = f"{gen_table_schema.module_name}:{_bn_perm}"
            _business_route_slug = Jinja2TemplateUtil.business_name_to_slug(gen_table_schema.business_name)
        # 创建菜单 CRUD 实例
        menu_crud = MenuCRUD(auth)
        if not gen_table_schema.function_name:
            raise CustomException(msg="功能名称不能为空")
        if not gen_table_schema.package_name:
            raise CustomException(msg="包名不能为空")
        await cls._assert_parent_menu_is_catalog(auth, gen_table_schema.parent_menu_id)
        # 1. 目录 + 菜单 + 按钮：先取/建模块目录（名称规则见 _catalog_menu_dir_key）
        dir_menu_id = await cls._get_or_create_package_directory_menu(
            menu_crud,
            gen_table_schema.parent_menu_id,
            gen_table_schema.package_name,
            gen_table_schema.module_name,
            gen_table_schema.business_name or "",
        )

        # 检查同一模块目录下是否已有同名功能菜单（避免与其它模块下的同名功能冲突）
        existing_func_menu = await menu_crud.get(
            name=gen_table_schema.function_name,
            type=_MENU_TYPE_MENU,
            parent_id=dir_menu_id,
        )
        if existing_func_menu:
            raise CustomException(
                msg=f"该模块目录下功能菜单「{gen_table_schema.function_name}」已存在，不能重复创建"
            )
        route_seg = cls._menu_route_first_segment(
            gen_table_schema.parent_menu_id,
            gen_table_schema.package_name or "",
            gen_table_schema.module_name,
        )
        if is_ex:
            _pn = (gen_table_schema.package_name or "").strip()
            _mn = (gen_table_schema.module_name or "").strip()
            _bn = (gen_table_schema.business_name or "").strip()
            _rsegs = [route_seg, _mn]
            if _bn:
                _rsegs.extend(s for s in _bn.split("/") if s)
            _route_path = "/" + "/".join(_rsegs)
            _component_path = f"{_pn}/{_mn}" + (f"/{_bn}" if _bn else "") + "/index"
        else:
            _route_path = f"/{route_seg}/{gen_table_schema.business_name}"
            _component_path = f"{gen_table_schema.module_name}/{gen_table_schema.business_name}/index"
        # 创建功能菜单（类型=2：菜单）
        parent_menu = await menu_crud.create(
            MenuCreateSchema(
                name=gen_table_schema.function_name,
                type=_MENU_TYPE_MENU,
                order=9999,
                permission=f"{permission_prefix}:query",
                icon="menu",
                route_name=CamelCaseUtil.snake_to_camel(_business_route_slug),
                route_path=_route_path,
                component_path=_component_path,
                redirect=None,
                hidden=False,
                keep_alive=True,
                always_show=False,
                title=gen_table_schema.function_name,
                params=None,
                affix=False,
                parent_id=dir_menu_id,  # 使用目录菜单ID或用户指定的parent_menu_id作为父ID
                status="0",
                description=f"{gen_table_schema.function_name}功能菜单",
            )
        )
        # 创建按钮权限（类型=3：按钮/权限）
        buttons = [
            {
                "name": f"{gen_table_schema.function_name}查询",
                "permission": f"{permission_prefix}:query",
                "order": 1,
            },
            {
                "name": f"{gen_table_schema.function_name}详情",
                "permission": f"{permission_prefix}:detail",
                "order": 2,
            },
            {
                "name": f"{gen_table_schema.function_name}新增",
                "permission": f"{permission_prefix}:create",
                "order": 3,
            },
            {
                "name": f"{gen_table_schema.function_name}修改",
                "permission": f"{permission_prefix}:update",
                "order": 4,
            },
            {
                "name": f"{gen_table_schema.function_name}删除",
                "permission": f"{permission_prefix}:delete",
                "order": 5,
            },
            {
                "name": f"{gen_table_schema.function_name}批量状态修改",
                "permission": f"{permission_prefix}:patch",
                "order": 6,
            },
            {
                "name": f"{gen_table_schema.function_name}导出",
                "permission": f"{permission_prefix}:export",
                "order": 7,
            },
            {
                "name": f"{gen_table_schema.function_name}导入",
                "permission": f"{permission_prefix}:import",
                "order": 8,
            },
            {
                "name": f"{gen_table_schema.function_name}下载导入模板",
                "permission": f"{permission_prefix}:download",
                "order": 9,
            },
        ]
        for button in buttons:
            # 检查按钮权限是否已存在
            await menu_crud.create(
                MenuCreateSchema(
                    name=button["name"],
                    type=3,
                    order=button["order"],
                    permission=button["permission"],
                    icon=None,
                    route_name=None,
                    route_path=None,
                    component_path=None,
                    redirect=None,
                    hidden=False,
                    keep_alive=True,
                    always_show=False,
                    title=button["name"],
                    params=None,
                    affix=False,
                    parent_id=parent_menu.id,
                    status="0",
                    description=f"{gen_table_schema.function_name}功能按钮",
                )
            )
            log.info(f"成功创建按钮权限: {button['name']}")
        log.info(f"成功创建{gen_table_schema.function_name}菜单及按钮权限")

        # 2. 菜单创建成功后，再生成页面代码（主表 + 可选子表）
        async def _write_templates(
            templates: list[str], ctx: dict[str, Any], table_schema: GenTableOutSchema
        ) -> None:
            for template in templates:
                try:
                    render_content = await env.get_template(template).render_async(**ctx)
                    file_name = Jinja2TemplateUtil.get_file_name(template, table_schema)
                    full_path = BASE_DIR.parent.joinpath(file_name)
                    gen_path = str(full_path)
                    if not gen_path:
                        raise CustomException(msg="【代码生成】生成路径为空")
                    os.makedirs(os.path.dirname(gen_path), exist_ok=True)
                    await anyio.Path(gen_path).write_text(render_content, encoding="utf-8")
                    plugin_root = (
                        (table_schema.package_name or "").strip()
                        if cls._is_example_style(table_schema.package_name, table_schema.module_name)
                        else (table_schema.module_name or "").strip()
                    )
                    if plugin_root:
                        module_init_path = BASE_DIR.parent.joinpath(
                            f"backend/app/plugin/{plugin_root}/__init__.py"
                        )
                        if not module_init_path.exists():
                            os.makedirs(os.path.dirname(module_init_path), exist_ok=True)
                            await anyio.Path(module_init_path).write_text(
                                "# -*- coding: utf-8 -*-", encoding="utf-8"
                            )
                except Exception as e:
                    raise CustomException(
                        msg=f"渲染模板失败，表名：{table_schema.table_name}，详细错误信息：{e!s}"
                    )

        await _write_templates(render_info[0], render_info[2], gen_table_schema)
        if gen_table_schema.sub and gen_table_schema.sub_table:
            sub_ctx = Jinja2TemplateUtil.prepare_sub_render_context(
                gen_table_schema, gen_table_schema.sub_table
            )
            await _write_templates(render_info[0], sub_ctx, gen_table_schema.sub_table)

        return True

    @classmethod
    @handle_service_exception
    async def batch_gen_code_service(cls, auth: AuthSchema, table_names: list[str]) -> bytes:
        """
        批量生成代码并打包为ZIP。
        - 备注：内存生成并压缩，兼容多模板类型；供下载使用。

        参数:
        - auth (AuthSchema): 认证信息。
        - table_names (list[str]): 业务表名列表。

        返回:
        - bytes: 包含所有生成代码的ZIP文件内容。
        """
        valid_names = [t.strip() for t in table_names if t and str(t).strip()]
        if not valid_names:
            raise CustomException(msg="表名列表不能为空")
        zip_buffer = io.BytesIO()
        file_count = 0
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for table_name in valid_names:
                try:
                    env = Jinja2TemplateUtil.get_env()
                    render_info = await cls.__get_gen_render_info(auth, table_name)
                    gen_tbl = render_info[3]
                    for template_file, output_file in zip(
                        render_info[0], render_info[1], strict=False
                    ):
                        render_content = await env.get_template(template_file).render_async(
                            **render_info[2]
                        )
                        zip_file.writestr(output_file, render_content)
                        file_count += 1
                    if gen_tbl.sub and gen_tbl.sub_table:
                        sub_ctx = Jinja2TemplateUtil.prepare_sub_render_context(
                            gen_tbl, gen_tbl.sub_table
                        )
                        sub_tbl = gen_tbl.sub_table
                        for template_file in render_info[0]:
                            render_content = await env.get_template(template_file).render_async(
                                **sub_ctx
                            )
                            out_path = Jinja2TemplateUtil.get_file_name(template_file, sub_tbl)
                            zip_file.writestr(out_path, render_content)
                            file_count += 1
                except Exception as e:
                    log.error(f"批量生成代码时处理表 {table_name} 出错: {e!s}")
                    # 继续处理其他表，不中断整个过程
                    continue
        zip_data = zip_buffer.getvalue()
        zip_buffer.close()
        if file_count == 0:
            raise CustomException(
                msg="未能生成任何代码文件：请检查所选表是否存在于代码生成配置中，或主子表、字段配置是否正确"
            )
        return zip_data

    @classmethod
    @handle_service_exception
    async def sync_db_service(cls, auth: AuthSchema, table_name: str) -> None:
        """
        同步数据库表结构到业务表。

        参数:
        - auth (AuthSchema): 认证信息。
        - table_name (str): 业务表名。

        返回:
        - None
        """
        # 验证表名非空
        if not table_name or not table_name.strip():
            raise CustomException(msg="表名不能为空")
        gen_table = await GenTableCRUD(auth).get_gen_table_by_name(table_name)
        if not gen_table:
            raise CustomException(msg="业务表不存在")
        table = GenTableOutSchema.model_validate(gen_table)
        if not table.id:
            raise CustomException(msg="业务表ID不能为空")
        table_columns = table.columns or []
        table_column_map = {column.column_name: column for column in table_columns}
        # 确保db_table_columns始终是列表类型，避免None值
        db_table_columns = (
            await GenTableColumnCRUD(auth).get_gen_db_table_columns_by_name(table_name) or []
        )
        db_table_columns = [col for col in db_table_columns if col is not None]
        db_table_column_names = [column.column_name for column in db_table_columns]
        try:
            for column in db_table_columns:
                GenUtils.init_column_field(column, table)
                if column.column_name in table_column_map:
                    prev_column = table_column_map[column.column_name]
                    if hasattr(prev_column, "id") and prev_column.id:
                        column.id = prev_column.id
                    if hasattr(prev_column, "dict_type") and prev_column.dict_type:
                        column.dict_type = prev_column.dict_type
                    if hasattr(prev_column, "query_type") and prev_column.query_type:
                        column.query_type = prev_column.query_type
                    if hasattr(prev_column, "html_type") and prev_column.html_type:
                        column.html_type = prev_column.html_type
                    is_pk_bool = False
                    if hasattr(prev_column, "is_pk"):
                        is_pk_bool = (
                            prev_column.is_pk
                            if isinstance(prev_column.is_pk, bool)
                            else str(prev_column.is_pk) == "1"
                        )
                    if hasattr(prev_column, "is_nullable") and not is_pk_bool:
                        column.is_nullable = prev_column.is_nullable
                    if hasattr(prev_column, "python_field"):
                        column.python_field = prev_column.python_field or column.python_field
                    if hasattr(column, "id") and column.id:
                        await GenTableColumnCRUD(auth).update_gen_table_column_crud(
                            column.id, column
                        )
                    else:
                        await GenTableColumnCRUD(auth).create_gen_table_column_crud(column)
                else:
                    # 设置table_id以确保新字段能正确关联到表
                    column.table_id = table.id
                    await GenTableColumnCRUD(auth).create_gen_table_column_crud(column)
            del_columns = [
                column
                for column in table_columns
                if column.column_name not in db_table_column_names
            ]
            if del_columns:
                for column in del_columns:
                    if hasattr(column, "id") and column.id:
                        await GenTableColumnCRUD(auth).delete_gen_table_column_by_column_id_crud([
                            column.id
                        ])
        except Exception as e:
            raise CustomException(msg=f"同步失败: {e!s}")

    @classmethod
    async def hydrate_sub_table(cls, auth: AuthSchema, gen_table: GenTableOutSchema) -> None:
        """从数据库加载子表列结构，填充 ``sub_table`` 并设置 ``sub``。"""
        gen_table.master_sub_hint = None
        sub_name_raw = (gen_table.sub_table_name or "").strip()
        fk_raw = (gen_table.sub_table_fk_name or "").strip()
        if not sub_name_raw and not fk_raw:
            gen_table.sub = False
            gen_table.sub_table = None
            return
        if sub_name_raw and not fk_raw:
            gen_table.sub = False
            gen_table.sub_table = None
            gen_table.master_sub_hint = "已填写子表表名，请同时填写「子表外键列」后再保存"
            return
        if fk_raw and not sub_name_raw:
            gen_table.sub = False
            gen_table.sub_table = None
            gen_table.master_sub_hint = "已填写子表外键列，请同时填写「子表表名」后再保存"
            return
        if sub_name_raw == (gen_table.table_name or "").strip():
            gen_table.sub = False
            gen_table.sub_table = None
            gen_table.master_sub_hint = "子表表名不能与主表表名相同"
            return
        try:
            gen_table_columns = await GenTableColumnCRUD(auth).get_gen_db_table_columns_by_name(
                sub_name_raw
            )
        except Exception as e:
            log.warning(f"获取子表 {sub_name_raw} 字段失败: {e!s}")
            gen_table.sub = False
            gen_table.sub_table = None
            gen_table.master_sub_hint = f"无法读取子表结构：{e!s}"
            return
        if not gen_table_columns:
            gen_table.sub = False
            gen_table.sub_table = None
            gen_table.master_sub_hint = (
                f"当前数据库中不存在表「{sub_name_raw}」或该表无列，请先建表再配置主子表"
            )
            return
        fk_names = {c.column_name for c in gen_table_columns if c.column_name}
        if fk_raw not in fk_names:
            gen_table.sub = False
            gen_table.sub_table = None
            gen_table.master_sub_hint = (
                f"子表「{sub_name_raw}」中不存在名为「{fk_raw}」的列，请核对外键列名"
            )
            return
        table_comment = await GenTableCRUD(auth).get_db_table_comment(sub_name_raw)
        sub = GenTableOutSchema(
            id=-1,
            table_name=sub_name_raw,
            table_comment=table_comment or None,
            class_name=GenUtils.convert_class_name(sub_name_raw),
            package_name=gen_table.package_name,
            module_name=gen_table.module_name,
            business_name=sub_name_raw,
            function_name=re.sub(r"(?:表|测试)", "", table_comment or "") or sub_name_raw,
            sub_table_name=None,
            sub_table_fk_name=None,
            parent_menu_id=gen_table.parent_menu_id,
            columns=[],
            sub=False,
            sub_table=None,
        )
        for column in gen_table_columns:
            col_dump = column.model_dump()
            col_dump["table_id"] = -1
            col_schema = GenTableColumnSchema.model_validate(col_dump)
            GenUtils.init_column_field(col_schema, sub)
            sub.columns.append(GenTableColumnOutSchema(**col_schema.model_dump()))
        await cls.set_pk_column(sub)
        gen_table.sub = True
        gen_table.sub_table = sub
        gen_table.master_sub_hint = None

    @classmethod
    def _assert_master_sub_config_valid(cls, gen_table: GenTableOutSchema) -> None:
        """预览/生成前校验主子表配置是否可用。"""
        sn = (gen_table.sub_table_name or "").strip()
        fk = (gen_table.sub_table_fk_name or "").strip()
        if not sn and not fk:
            return
        if not sn or not fk:
            raise CustomException(
                msg=gen_table.master_sub_hint
                or "子表表名与子表外键列须同时填写或同时留空"
            )
        if not gen_table.sub_table:
            raise CustomException(
                msg=gen_table.master_sub_hint
                or "无法生成主子表代码：请确认子表已在当前数据库中存在，且外键列名正确"
            )

    @classmethod
    async def set_pk_column(cls, gen_table: GenTableOutSchema) -> None:
        """设置主键列信息（主表/子表）。
        - 备注：同时兼容`pk`布尔与`is_pk == '1'`字符串两种标识。

        参数:
        - gen_table (GenTableOutSchema): 业务表详细信息模型。

        返回:
        - None
        """
        if gen_table.columns:
            for column in gen_table.columns:
                is_pk = getattr(column, "is_pk", False)
                if bool(is_pk) if isinstance(is_pk, bool) else str(is_pk) == "1":
                    gen_table.pk_column = column
                    break
        # 如果没有找到主键列且有列存在，使用第一个列作为主键
        if gen_table.pk_column is None and gen_table.columns:
            gen_table.pk_column = gen_table.columns[0]

    @classmethod
    async def __get_gen_render_info(cls, auth: AuthSchema, table_name: str) -> list[Any]:
        """
        获取生成代码渲染模板相关信息。

        参数:
        - auth (AuthSchema): 认证对象。
        - table_name (str): 业务表名称。

        返回:
        - list[Any]: [模板列表, 输出文件名列表, 渲染上下文, 业务表对象]。

        异常:
        - CustomException: 当业务表不存在或数据转换失败时抛出。
        """
        gen_table_model = await GenTableCRUD(auth=auth).get_gen_table_by_name(table_name)
        # 检查表是否存在
        if gen_table_model is None:
            raise CustomException(msg=f"业务表 {table_name} 不存在")
        gen_table = GenTableOutSchema.model_validate(gen_table_model)
        await cls.set_pk_column(gen_table)
        await cls.hydrate_sub_table(auth, gen_table)
        cls._assert_master_sub_config_valid(gen_table)
        context = Jinja2TemplateUtil.prepare_context(gen_table)
        template_list = Jinja2TemplateUtil.get_template_list()
        output_files = [
            Jinja2TemplateUtil.get_file_name(template, gen_table) for template in template_list
        ]
        return [template_list, output_files, context, gen_table]


class GenTableColumnService:
    """代码生成业务表字段服务层"""

    @classmethod
    @handle_service_exception
    async def get_gen_table_column_list_by_table_id_service(
        cls, auth: AuthSchema, table_id: int
    ) -> list[dict[str, Any]]:
        """获取业务表字段列表信息（输出模型）。

        参数:
        - auth (AuthSchema): 认证信息。
        - table_id (int): 业务表ID。

        返回:
        - list[dict[str, Any]]: 业务表字段列表，每个元素为字段详细信息字典。
        """
        gen_table_column_list_result = await GenTableColumnCRUD(auth).list_gen_table_column_crud({
            "table_id": table_id
        })
        result = [
            GenTableColumnOutSchema.model_validate(gen_table_column).model_dump()
            for gen_table_column in gen_table_column_list_result
        ]
        return result

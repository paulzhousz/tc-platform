from dataclasses import dataclass

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.common.enums import QueueEnum
from app.core.base_schema import BaseSchema


class GenDBTableSchema(BaseModel):
    """数据库中的表信息（跨方言统一结构）。
    - 供“导入表结构”与“同步结构”环节使用。
    """

    model_config = ConfigDict(from_attributes=True)

    database_name: str | None = Field(default=None, description="数据库名称")
    table_name: str | None = Field(default=None, description="表名称")
    table_type: str | None = Field(default=None, description="表类型")
    table_comment: str | None = Field(default=None, description="表描述")


class GenCreateTableSqlBody(BaseModel):
    """从代码生成页提交的建表 SQL（JSON 对象，便于与前端 axios 一致）。"""

    sql: str = Field(..., description="CREATE TABLE 等 DDL，可多条语句")


class GenTableColumnSchema(BaseModel):
    """代码生成业务表字段创建模型（原始字段+生成配置）。
    - 从根本上解决问题：所有字段都设置了合理的默认值，避免None值问题
    """

    model_config = ConfigDict(from_attributes=True)

    table_id: int = Field(default=0, description="归属表编号")
    column_name: str = Field(default="", description="列名称")
    column_comment: str | None = Field(default="", description="列描述")
    column_type: str = Field(default="varchar(255)", description="列类型")
    column_length: str | None = Field(default="", description="列长度")
    column_default: str | None = Field(default="", description="列默认值")
    is_pk: bool = Field(default=False, description="是否主键（True是 False否）")
    is_increment: bool = Field(default=False, description="是否自增（True是 False否）")
    is_nullable: bool = Field(default=True, description="是否允许为空（True是 False否）")
    is_unique: bool = Field(default=False, description="是否唯一（True是 False否）")
    python_type: str = Field(default="str", description="python类型")
    python_field: str = Field(default="", description="python字段名")
    is_insert: bool = Field(default=True, description="是否为插入字段（True是 False否）")
    is_edit: bool = Field(default=True, description="是否编辑字段（True是 False否）")
    is_list: bool = Field(default=True, description="是否列表字段（True是 False否）")
    is_query: bool = Field(default=True, description="是否查询字段（True是 False否）")
    query_type: str | None = Field(
        default=None, description="查询方式（等于、不等于、大于、小于、范围）"
    )
    html_type: str | None = Field(
        default="input",
        description="显示类型（文本框、文本域、下拉框、复选框、单选框、日期控件）",
    )
    dict_type: str | None = Field(default="", description="字典类型")
    sort: int = Field(default=0, description="排序")


class GenTableColumnOutSchema(GenTableColumnSchema, BaseSchema):
    """
    业务表字段输出模型
    """

    model_config = ConfigDict(from_attributes=True)

    super_column: str | None = Field(default="0", description="是否为基类字段（1是 0否）")


class GenTableSchema(BaseModel):
    """代码生成业务表更新模型（扩展聚合字段）。
    - 聚合：`columns`字段包含字段列表；`pk_column`主键字段；子表结构`sub_table`。
    """

    """代码生成业务表基础模型（创建/更新共享字段）。
    - 说明：`params`为前端结构体，后端持久化为`options`的JSON。
    """
    model_config = ConfigDict(from_attributes=True)

    table_name: str = Field(..., description="表名称")
    table_comment: str | None = Field(default=None, description="表描述")
    class_name: str | None = Field(default=None, description="实体类名称")
    package_name: str | None = Field(default=None, description="生成包路径")
    module_name: str | None = Field(default=None, description="生成模块名")
    business_name: str | None = Field(
        default=None,
        description=(
            "功能子目录/路由段；导入时默认表名；同 module_name 下多表须不同。"
            "可含斜杠表示嵌套，参考 module_example：demo、demo/demo01、gen_demo02。"
        ),
    )
    function_name: str | None = Field(default=None, description="生成功能名")
    sub_table_name: str | None = Field(default=None, description="关联子表的表名")
    sub_table_fk_name: str | None = Field(default=None, description="子表关联的外键名")
    parent_menu_id: int | None = Field(
        default=None,
        description=(
            "写入本地须选目录类型。有值：侧栏 上级/短包名/功能/按钮，页面路由 /包名/业务名。"
            "留空：侧栏 module_包名/功能/按钮，页面路由 /module_包名/业务名（与 plugin 一致）；"
            "后端 HTTP 接口仍为 /短名（module_xxx→/xxx）。"
        ),
    )
    description: str | None = Field(default=None, max_length=255, description="描述")

    columns: list["GenTableColumnOutSchema"] | None = Field(default=None, description="表列信息")

    @field_validator("table_name")
    @classmethod
    def table_name_update(cls, v: str) -> str:
        """更新表名称"""
        if not v:
            raise ValueError("表名称不能为空")
        return v

    @field_validator("sub_table_name", "sub_table_fk_name", mode="before")
    @classmethod
    def strip_optional_sub_fields(cls, v: str | None) -> str | None:
        """主子表字段去首尾空格，空串视为未填。"""
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None


class GenTableOutSchema(GenTableSchema, BaseSchema):
    """业务表输出模型（面向控制器/前端）。"""

    model_config = ConfigDict(from_attributes=True)

    pk_column: GenTableColumnOutSchema | None = Field(default=None, description="主键信息")
    sub_table: GenTableSchema | None = Field(default=None, description="子表信息")
    sub: bool | None = Field(default=None, description="是否为子表")
    master_sub_hint: str | None = Field(
        default=None,
        description="主子表配置说明或异常提示（仅接口输出，不落库）",
    )


@dataclass
class GenTableQueryParam:
    """代码生成业务表查询参数
    - 支持按`table_name`、`table_comment`进行模糊检索（由CRUD层实现like）。
    - 空值将被忽略，不参与过滤。
    """

    def __init__(
        self,
        table_name: str | None = Query(None, description="表名称"),
        table_comment: str | None = Query(None, description="表注释"),
    ) -> None:
        # 模糊查询字段
        self.table_name = (QueueEnum.like.value, table_name)
        self.table_comment = (QueueEnum.like.value, table_comment)


class GenTableColumnQueryParam:
    """代码生成业务表字段查询参数
    - `column_name`按like规则模糊查询（透传到CRUD层）
    """

    def __init__(
        self,
        column_name: str | None = Query(None, description="列名称"),
    ) -> None:
        # 模糊查询字段：约定("like", 值)格式，便于CRUD解析
        self.column_name = (QueueEnum.like.value, column_name)

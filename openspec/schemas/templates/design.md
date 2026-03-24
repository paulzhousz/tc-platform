## 后端架构设计

### 目录结构

```
backend/app/plugin/module_<模块名>/<子模块名>/
├── __init__.py
├── model.py
├── schema.py
├── crud.py
├── service.py
└── controller.py
```

### 1. Model 层

**文件**: `model.py`

**关键设计**:
- 使用 SQLAlchemy 2.0 `Mapped` 和 `mapped_column`
- 继承 `ModelMixin` 和 `UserMixin`
- 常用查询字段添加 `index=True`
- 业务枚举在 `model.py` 文件顶部定义
- 表名格式：`<模块简称>_<实体名>`（如 `task_job`）
- 使用 `__loader_options__` 预加载用户关系

```python
# 示例骨架
import enum
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import ModelMixin, UserMixin


class XxxStatusEnum(enum.Enum):
    """状态枚举"""
    ACTIVE = "0"      # 启用
    INACTIVE = "1"    # 禁用


class XxxModel(ModelMixin, UserMixin):
    __tablename__ = "product_product"  # 模块简称_实体名
    __loader_options__ = ["created_by", "updated_by"]

    # ModelMixin 提供: id, uuid, status, description, created_time, updated_time
    # UserMixin 提供: created_id, updated_id, created_by, updated_by

    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="名称")
    # 其他业务字段...
```

### 2. Schema 层

**文件**: `schema.py`

| Schema | 用途 | 继承 |
|--------|------|------|
| XxxCreateSchema | 创建请求 | BaseModel |
| XxxUpdateSchema | 更新请求 | 继承 CreateSchema |
| XxxOutSchema | 响应输出 | CreateSchema, BaseSchema, UserBySchema |
| XxxQueryParam | 查询参数 | @dataclass |

### 3. CRUD 层

**文件**: `crud.py`

继承 `CRUDBase[ModelType, CreateSchemaType, UpdateSchemaType]`，使用 `auth: AuthSchema` 初始化。

方法清单:
- `get(id, preload)` - 根据 ID 获取单个对象
- `list(search, order_by, preload)` - 获取列表
- `page(offset, limit, order_by, search, out_schema, preload)` - 分页查询
- `create(data)` - 创建（自动设置 created_id）
- `update(id, data)` - 更新（自动设置 updated_id）
- `delete(ids)` - 批量删除
- `set(ids, **kwargs)` - 批量更新字段

### 4. Service 层

**文件**: `service.py`

- 使用 `@classmethod` 装饰器
- 第一个参数为 `auth: AuthSchema`
- CRUD 实例在方法内创建
- 使用 `CustomException(msg="...")` 抛出业务异常

### 5. Controller 层

**文件**: `controller.py`

- 使用 `Annotated` 类型提示
- 权限通过 `AuthPermission(["权限标识"])` 注入
- 分页参数使用 `PaginationQueryParam`

**API 接口**:
| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/<模块名>/<子模块名>/list` | 列表查询（分页） |
| GET | `/<模块名>/<子模块名>/detail/{id}` | 详情查询 |
| POST | `/<模块名>/<子模块名>/create` | 创建 |
| PUT | `/<模块名>/<子模块名>/update/{id}` | 更新（id 在路径中） |
| DELETE | `/<模块名>/<子模块名>/delete` | 删除（body 传递 id 数组） |

---

## 前端设计

### Web 端

**目录**:
- API: `frontend/src/api/module_<模块名>/<子模块>.ts`
- 页面: `frontend/src/views/module_<模块名>/<子模块>/index.vue`

**分页参数**: `page_no`, `page_size`（不是 `page`）

**组件**:
- 搜索表单
- 数据表格
- 新增/编辑对话框
- 分页组件

### 移动端

**目录**:
- 列表页: `src/pages/<模块名>/index.vue`
- 详情页: `src/pages/<模块名>/detail.vue`

**HTTP 导入**: `import { http } from '@/http'`

**方法**: `http.Get`, `http.Post`, `http.Put`, `http.Delete`（大写开头）

---

## 权限设计

| 权限标识 | 说明 |
|----------|------|
| `module_<模块名>:<子模块名>:list` | 列表查询 |
| `module_<模块名>:<子模块名>:detail` | 详情查询 |
| `module_<模块名>:<子模块名>:create` | 创建 |
| `module_<模块名>:<子模块名>:update` | 更新 |
| `module_<模块名>:<子模块名>:delete` | 删除 |

---

## 文件清单

### 后端文件

- [ ] `backend/app/plugin/module_<模块名>/<子模块名>/__init__.py`
- [ ] `backend/app/plugin/module_<模块名>/<子模块名>/model.py`
- [ ] `backend/app/plugin/module_<模块名>/<子模块名>/schema.py`
- [ ] `backend/app/plugin/module_<模块名>/<子模块名>/crud.py`
- [ ] `backend/app/plugin/module_<模块名>/<子模块名>/service.py`
- [ ] `backend/app/plugin/module_<模块名>/<子模块名>/controller.py`

### Web 前端文件

- [ ] `frontend/src/api/module_<模块名>/<子模块>.ts`
- [ ] `frontend/src/views/module_<模块名>/<子模块>/index.vue`

### 移动端文件（可选）

- [ ] `src/pages/<模块名>/index.vue`
- [ ] `src/pages/<模块名>/detail.vue`
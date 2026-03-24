## 数据模型设计

### 表结构

**表名**: `<模块简称>_<实体名>`

> 注意：`sys_` 前缀仅用于系统核心模块（`app/api/v1/module_system/`），Plugin 模块使用模块简称（如 `task_job`, `app_myapp`）

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| id | Integer | Y | 主键ID（ModelMixin 提供） |
| uuid | String(64) | Y | 唯一标识（ModelMixin 提供） |
| <!-- 业务字段 --> | | | |
| status | String(16) | N | 状态（引用枚举） |
| description | Text | N | 描述（ModelMixin 提供） |
| created_id | Integer | N | 创建人ID（UserMixin 提供） |
| created_time | DateTime | N | 创建时间（ModelMixin 提供） |
| updated_id | Integer | N | 更新人ID（UserMixin 提供） |
| updated_time | DateTime | N | 更新时间（ModelMixin 提供） |

> **重要**：ModelMixin 提供 id, uuid, status, description, created_time, updated_time
> UserMixin 提供 created_id, updated_id, created_by, updated_by（关系）

### 枚举定义

在模块自己的 `model.py` 文件顶部定义：

```python
import enum

class XxxStatusEnum(enum.Enum):
    """XXX状态枚举"""
    ACTIVE = "0"      # 启用
    INACTIVE = "1"    # 禁用
```

> 注意：`app/common/enums.py` 是系统内置枚举（QueueEnum 等），勿修改

---

## API 接口规格

### 1. 列表查询

**端点**: `GET /<模块名>/<子模块名>/list`

**权限**: `module_<模块名>:<子模块名>:list`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page_no | int | Y | 页码（从 1 开始） |
| page_size | int | Y | 每页数量 |
| <!-- 查询条件 --> | | | |

**响应**:

```json
{
  "code": 200,
  "data": {
    "items": [],
    "total": 0,
    "page_no": 1,
    "page_size": 10,
    "has_next": true
  }
}
```

### 2. 详情查询

**端点**: `GET /<模块名>/<子模块名>/detail/{id}`

**权限**: `module_<模块名>:<子模块名>:detail`

### 3. 创建

**端点**: `POST /<模块名>/<子模块名>/create`

**权限**: `module_<模块名>:<子模块名>:create`

**请求体**:

```json
{
  "name": "",
  "<!-- 其他字段 -->": ""
}
```

### 4. 更新

**端点**: `PUT /<模块名>/<子模块名>/update/{id}`

**权限**: `module_<模块名>:<子模块名>:update`

> **注意**：id 在 URL 路径中

### 5. 删除

**端点**: `DELETE /<模块名>/<子模块名>/delete`

**权限**: `module_<模块名>:<子模块名>:delete`

**请求体**: id 数组（支持批量删除）

```json
[1, 2, 3]
```

---

## 业务规则

### Requirement: <!-- 规则名称 -->

<!-- 规则描述 -->

#### Scenario: <!-- 场景名称 -->

- **GIVEN** <!-- 前置条件 -->
- **WHEN** <!-- 触发动作 -->
- **THEN** <!-- 预期结果 -->
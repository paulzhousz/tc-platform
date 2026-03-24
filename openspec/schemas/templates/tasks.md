## 1. 数据库层

- [ ] 1.1 创建 `model.py` - 在文件顶部定义枚举类，然后定义 ORM 模型（继承 ModelMixin, UserMixin）
- [ ] 1.2 生成数据库迁移文件：`python main.py revision --env=dev`
- [ ] 1.3 应用迁移：`python main.py upgrade --env=dev`

## 2. Schema 层

- [ ] 2.1 创建 `schema.py` - 定义 XxxCreateSchema（继承 BaseModel）
- [ ] 2.2 定义 XxxUpdateSchema（继承 CreateSchema）
- [ ] 2.3 定义 XxxOutSchema（继承 CreateSchema, BaseSchema, UserBySchema）
- [ ] 2.4 定义 XxxQueryParam（使用 @dataclass）

## 3. CRUD 层

- [ ] 3.1 创建 `crud.py` - 继承 CRUDBase，使用 auth: AuthSchema 初始化
- [ ] 3.2 实现 get_by_id_crud 方法
- [ ] 3.3 实现 page_crud 方法（分页查询）
- [ ] 3.4 实现 create_crud 方法
- [ ] 3.5 实现 update_crud 方法
- [ ] 3.6 实现 delete_crud 方法（批量删除）

## 4. Service 层

- [ ] 4.1 创建 `service.py` - 使用 @classmethod
- [ ] 4.2 实现 detail_service
- [ ] 4.3 实现 page_service
- [ ] 4.4 实现 create_service（包含名称重复校验）
- [ ] 4.5 实现 update_service
- [ ] 4.6 实现 delete_service（批量删除校验）

## 5. Controller 层

- [ ] 5.1 创建 `controller.py` - 配置 APIRouter（route_class=OperationLogRoute）
- [ ] 5.2 实现列表接口 `GET /list`（使用 PaginationQueryParam）
- [ ] 5.3 实现详情接口 `GET /detail/{id}`
- [ ] 5.4 实现创建接口 `POST /create`
- [ ] 5.5 实现更新接口 `PUT /update/{id}`（注意：id 在路径中）
- [ ] 5.6 实现删除接口 `DELETE /delete`（注意：body 传递 id 数组）

## 6. Web 前端

- [ ] 6.1 创建 API 文件 `src/api/module_<模块名>/<子模块>.ts`
- [ ] 6.2 定义 TypeScript 接口（PageQuery, XxxTable, XxxForm）
- [ ] 6.3 创建页面组件 `src/views/module_<模块名>/<子模块>/index.vue`
- [ ] 6.4 实现搜索表单
- [ ] 6.5 实现数据表格
- [ ] 6.6 实现新增/编辑对话框
- [ ] 6.7 配置路由

## 7. 移动端（可选）

- [ ] 7.1 创建列表页 `src/pages/<模块名>/index.vue`
- [ ] 7.2 创建详情页 `src/pages/<模块名>/detail.vue`
- [ ] 7.3 配置路由

## 8. 权限配置

- [ ] 8.1 在系统管理中创建菜单
- [ ] 8.2 配置菜单权限标识
- [ ] 8.3 配置按钮权限

## 9. 测试验证

- [ ] 9.1 使用 Swagger UI 测试 API 接口
- [ ] 9.2 验证权限控制
- [ ] 9.3 前端功能测试
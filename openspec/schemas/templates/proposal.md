## Why

<!-- 说明开发此模块的业务背景和需求来源 -->
<!-- 解决什么问题 -->

## What Changes

<!-- 列出新增或修改的功能点 -->

### 新增功能
-

### 修改功能
-

<!-- 如有破坏性变更，使用 **BREAKING** 标记 -->

## Capabilities

### New Capabilities

<!-- 使用 module_<模块名>-<子模块名> 格式 -->
- `module_<模块名>-<子模块名>`: <功能描述>

### Modified Capabilities

<!-- 需要修改的现有模块，如无则留空 -->

## Impact

### 数据库影响
- 新增表：`<模块简称>_<表名>`（如 `task_job`）

> 注意：`sys_` 前缀仅用于系统核心模块（`app/api/v1/module_system/`），Plugin 模块使用模块简称

### API 路由
- `/<模块名>/<子模块名>/*`

### 前端页面
- Web: `views/module_<模块名>/<子模块>/index.vue`
- 移动端: `pages/<模块名>/`

### 权限配置

| 权限标识 | 说明 |
|----------|------|
| `module_<模块名>:<子模块名>:list` | 列表查询 |
| `module_<模块名>:<子模块名>:detail` | 详情查询 |
| `module_<模块名>:<子模块名>:create` | 创建 |
| `module_<模块名>:<子模块名>:update` | 更新 |
| `module_<模块名>:<子模块名>:delete` | 删除 |

---

## Worktree 信息（自动生成）

<!-- 以下信息由系统自动填充，请勿手动修改 -->

**变更标识**: `<变更名>`

**Worktree 模式**: `是/否`

| 项目 | 值 |
|------|-----|
| 分支名称 | `feature/<变更名>` |
| Worktree 路径 | `.worktrees/<变更名>/` |
| 创建时间 | `YYYY-MM-DD HH:MM:SS` |
| 主仓库路径 | `<主仓库绝对路径>` |
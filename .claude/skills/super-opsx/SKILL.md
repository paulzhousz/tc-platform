---
name: super-opsx
description: Bridge skill that integrates OpenSpec spec management with Superpowers execution skills. Use when you want the best of both: structured specs from OpenSpec and proven development patterns from Superpowers. 触发词: "super-opsx", "OpenSpec", "spec-driven", "规格驱动开发".
---

# OpenSpec-Superpowers Bridge

整合 OpenSpec 的规格管理能力与 Superpowers 的执行技能，提供完整的 spec-driven development 工作流。

## 为什么要用这个 Skill

| OpenSpec 优势 | Superpowers 优势 | 整合优势 |
|--------------|-----------------|---------|
| 结构化规格 | TDD 流程 | 一次命令，享受两者所长 |
| Delta Specs | Subagent 驱动 | 规格驱动 + 执行保障 |
| 归档系统 | 代码审查 | 完整的开发生命周期 |
| 多项目支持 | 验证流程 | 高质量输出保证 |

## 命令

| 命令 | 说明 |
|------|------|
| `/super-opsx-explore` | 探索想法、调查问题、澄清需求 |
| `/super-opsx-propose` | 创建变更 + Superpowers brainstorming |
| `/super-opsx-apply` | 执行实现 + TDD + Subagent |
| `/super-opsx-archive` | 验证 + 归档 |

## 前置条件

1. **OpenSpec 已安装**
   ```bash
   npm install -g @anthropic-ai/openspec
   ```

2. **Superpowers 已启用**
   ```
   /plugin install superpowers@superpowers-marketplace
   ```

3. **项目已初始化**
   ```bash
   openspec init
   ```

## 使用流程

```
/super-opsx-explore <topic>
        │
        ├── 自由探索，无固定步骤
        ├── 可视化想法，调查代码库
        └── 结束时提议 /super-opsx-propose

/super-opsx-propose add-feature
        │
        ├── 调用 OpenSpec 创建变更目录
        ├── 调用 Superpowers brainstorming 探索需求
        └── 输出到 openspec/changes/add-feature/

/super-opsx-apply
        │
        ├── 读取 tasks.md
        ├── 调用 Superpowers executing-plans + TDD
        └── 遵循 Write Test → Implement → Verify 流程

/super-opsx-archive
        │
        ├── 调用 Superpowers verification
        ├── 调用 OpenSpec archive
        └── 合并 Delta Specs
```

## 工作流对比

**独立使用 OpenSpec：**
```
/opsx:explore → /opsx:propose → /opsx:apply → /opsx:archive
```

**独立使用 Superpowers：**
```
/brainstorm → /write-plan → /execute-plan
```

**整合使用（推荐）：**
```
/super-opsx-explore → /super-opsx-propose → /super-opsx-apply → /super-opsx-archive
         │                    │                    │                    │
         ▼                    ▼                    ▼                    ▼
      自由探索             OpenSpec             OpenSpec            OpenSpec
      +                    +                   +                   +
      可选 brainstorming   Superpowers         Superpowers         Superpowers
                          brainstorming        executing-plans     verification
```

## 参考文档

- **[format-mapping.md](references/format-mapping.md)** — OpenSpec 与 Superpowers 格式映射规则

## 独立使用

OpenSpec 和 Superpowers 仍可独立使用，本 skill 不修改任何现有系统：

- **纯 OpenSpec**：`/opsx:explore`, `/opsx:propose`, `/opsx:apply`, `/opsx:archive`
- **纯 Superpowers**：`/brainstorm`, `/write-plan`, `/execute-plan`

## 关键原则

1. **规格先行** — 在编写代码前先达成规格共识
2. **TDD 驱动** — 遵循测试驱动开发流程
3. **增量验证** — 每个阶段都有检查点和验证
4. **完整归档** — 保留完整的变更历史和上下文

## 变更历史查看

归档后可通过以下方式查看变更历史：

| 文件 | 用途 |
|------|------|
| `HISTORY.md` | 人类可读表格，快速浏览所有变更 |
| `INDEX.json` | 机器可读索引，程序处理 |

**HISTORY.md 示例：**

```markdown
# 变更历史

| 日期 | 变更 | 状态 | 新增 | 修改 |
|------|------|------|------|------|
| 03-20 | permission | ✅ | permission/rbac | auth/middleware |
| 03-18 | auth-system | ✅ | auth/jwt, auth/login | user/model |
```
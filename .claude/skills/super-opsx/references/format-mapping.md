# OpenSpec ↔ Superpowers 格式映射

本文档定义 OpenSpec 和 Superpowers 之间的文档对应关系和格式转换规则。

## 文档对应关系

| OpenSpec 文件 | Superpowers 文档 | 说明 |
|--------------|-----------------|------|
| `proposal.md` | brainstorming 输出 | intent, scope, approach |
| `specs/*.md` | design doc | requirements, scenarios |
| `design.md` | plan header | architecture decisions |
| `tasks.md` | plan steps | implementation checklist |

## 目录结构对比

### OpenSpec 结构

```
openspec/
├── specs/                    # 项目级规格（持久化）
│   ├── auth/
│   │   └── spec.md
│   └── user/
│       └── spec.md
├── changes/                  # 变更目录
│   ├── add-user-auth/
│   │   ├── proposal.md
│   │   ├── specs/
│   │   │   └── auth/
│   │   │       └── spec.md
│   │   ├── design.md
│   │   └── tasks.md
│   └── archive/              # 归档变更
│       ├── INDEX.json        # 机器可读索引
│       ├── HISTORY.md        # 人类可读历史
│       └── 2026-03-20-add-user-auth/
│           └── archive-metadata.json
└── config.json
```

### Superpowers 结构

```
docs/
└── superpowers/
    ├── specs/                # 设计规格
    │   └── 2026-03-20-auth-design.md
    └── plans/                # 实施计划
        └── 2026-03-20-auth-plan.md
```

## 格式转换规则

### proposal.md ↔ Brainstorming 输出

**OpenSpec proposal.md 格式：**

```markdown
## Why

[变更原因]

## What Changes

[变更内容]

## Capabilities

### New Capabilities
- ...

### Modified Capabilities
- ...

## Impact

### New Files
- ...

### Modified Files
- ...
```

**Superpowers brainstorming 输出格式：**

```markdown
# Design: <Topic>

## Problem

[问题描述]

## Solution

[解决方案]

## Architecture

[架构设计]

## Components

[组件说明]

## Data Flow

[数据流]

## Error Handling

[错误处理]

## Testing Strategy

[测试策略]
```

**转换映射：**

| OpenSpec | Superpowers | 转换规则 |
|----------|-------------|---------|
| Why | Problem | 直接映射 |
| What Changes | Solution | 提取核心变更 |
| design.md | Architecture | 合并到 design.md |
| specs/ | Components + Data Flow | 分布到 specs/ |

### tasks.md ↔ Plan Steps

**OpenSpec tasks.md 格式：**

```markdown
## 1. Infrastructure
- [ ] 1.1 Create JWT utility
- [ ] 1.2 Add token validation

## 2. API Endpoints
- [ ] 2.1 Implement login endpoint
- [ ] 2.2 Implement refresh endpoint

## 3. Testing
- [ ] 3.1 Unit tests for JWT
- [ ] 3.2 Integration tests for auth
```

**Superpowers plan 格式：**

```markdown
# Implementation Plan: <Feature>

## Overview

[概述]

## Tasks

### Task 1: Infrastructure

- [ ] **Step 1: Write failing test for JWT utility**
- [ ] **Step 2: Run test (expect failure)**
- [ ] **Step 3: Implement JWT utility**
- [ ] **Step 4: Run test (expect success)**
- [ ] **Step 5: Commit**

### Task 2: API Endpoints

...

## Verification

- [ ] All tests pass
- [ ] Lint passes
- [ ] Type check passes
```

**转换规则：**

```
OpenSpec Task → Superpowers Task (展开为 TDD 步骤)

1.1 Create JWT utility
    ↓
### Task 1: Create JWT utility
- [ ] Step 1: Write failing test
- [ ] Step 2: Run test (expect failure)
- [ ] Step 3: Implement
- [ ] Step 4: Run test (expect success)
- [ ] Step 5: Commit
```

### Delta Specs 格式

**Delta Spec 结构：**

```markdown
# Delta Spec: <Change Name>

## Status
- [x] ADDED
- [ ] MODIFIED
- [ ] REMOVED

## Changes

### ADDED

#### auth/jwt

```yaml
description: JWT token generation and validation
operations:
  - generateToken(userId: string): string
  - validateToken(token: string): TokenPayload
```

### MODIFIED

#### user/model

```yaml
changes:
  - added field: authProvider
  - added field: lastLoginAt
```

### REMOVED

(none in this change)
```

## 双向同步规则

### OpenSpec → Superpowers

当需要将 OpenSpec 内容转换为 Superpowers 格式时：

1. **proposal.md → design doc**
   - 提取 Why → Problem
   - 提取 What Changes → Solution
   - 提取 design.md 架构部分

2. **tasks.md → plan**
   - 每个任务展开为 5 步 TDD 循环
   - 添加验证步骤

### Superpowers → OpenSpec

当需要将 Superpowers 内容转换为 OpenSpec 格式时：

1. **design doc → OpenSpec 结构**
   - Problem → proposal.md (Why)
   - Solution → proposal.md (What Changes)
   - Architecture → design.md
   - Components → specs/

2. **plan → tasks.md**
   - 合并 TDD 步骤为单个任务
   - 保留 checkbox 格式

## 工作流映射

### 独立工作流

| 阶段 | OpenSpec | Superpowers |
|------|----------|-------------|
| 规划 | `/opsx:propose` | `/brainstorm` |
| 详细设计 | 手动编写 specs/ | `/write-plan` |
| 实施 | `/opsx:apply` | `/execute-plan` |
| 验证 | `/opsx:verify` | `verification-before-completion` |
| 归档 | `/opsx:archive` | 无 |

### 整合工作流

| 阶段 | super-opsx 命令 | 内部调用 |
|------|-----------------|---------|
| 规划 | `/super-opsx:propose` | OpenSpec new + Superpowers brainstorming |
| 实施 | `/super-opsx:apply` | Superpowers TDD + executing-plans |
| 验证+归档 | `/super-opsx:archive` | Superpowers verification + OpenSpec archive |

## 示例：完整转换

### 输入：OpenSpec tasks.md

```markdown
## 1. Authentication
- [ ] 1.1 Implement JWT utility
- [ ] 1.2 Create login endpoint
- [ ] 1.3 Add refresh token logic

## 2. Authorization
- [ ] 2.1 Implement role checking
- [ ] 2.2 Add permission middleware
```

### 输出：Superpowers plan

```markdown
# Implementation Plan: Authentication System

## Overview
Implement JWT-based authentication with refresh token support and role-based authorization.

## Tasks

### Task 1: Implement JWT utility
- [ ] **Step 1: Write failing test for JWT generation**
- [ ] **Step 2: Run test (expect failure)**
- [ ] **Step 3: Implement JWT generation**
- [ ] **Step 4: Run test (expect success)**
- [ ] **Step 5: Commit: feat(auth): add JWT utility**

### Task 2: Create login endpoint
- [ ] **Step 1: Write failing test for login endpoint**
- [ ] **Step 2: Run test (expect failure)**
- [ ] **Step 3: Implement login endpoint**
- [ ] **Step 4: Run test (expect success)**
- [ ] **Step 5: Commit: feat(auth): add login endpoint**

### Task 3: Add refresh token logic
- [ ] **Step 1: Write failing test for refresh token**
- [ ] **Step 2: Run test (expect failure)**
- [ ] **Step 3: Implement refresh token logic**
- [ ] **Step 4: Run test (expect success)**
- [ ] **Step 5: Commit: feat(auth): add refresh token logic**

### Task 4: Implement role checking
- [ ] **Step 1: Write failing test for role checking**
- [ ] **Step 2: Run test (expect failure)**
- [ ] **Step 3: Implement role checking**
- [ ] **Step 4: Run test (expect success)**
- [ ] **Step 5: Commit: feat(auth): add role checking**

### Task 5: Add permission middleware
- [ ] **Step 1: Write failing test for permission middleware**
- [ ] **Step 2: Run test (expect failure)**
- [ ] **Step 3: Implement permission middleware**
- [ ] **Step 4: Run test (expect success)**
- [ ] **Step 5: Commit: feat(auth): add permission middleware**

## Verification
- [ ] All tests pass
- [ ] Lint passes
- [ ] Type check passes
- [ ] Manual testing complete
```

## 注意事项

1. **格式保真**：转换时应保留原始信息的完整性
2. **增量更新**：避免全量覆盖，支持增量同步
3. **冲突处理**：当两系统有冲突时，以 OpenSpec 为规格真相来源
4. **追溯性**：保留转换记录，支持双向追溯
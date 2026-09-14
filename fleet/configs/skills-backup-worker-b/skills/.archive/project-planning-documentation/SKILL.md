---
name: project-planning-documentation
description: "Create and optimize large-scale project planning documentation with milestones, dependency chains, multi-level step guides, rollback plans, and multi-perspective validation."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [planning, documentation, project-management, milestones, dependency-chains, risk-analysis]
    related_skills: [software-development/writing-plans, openclaw-imports/planning-with-files]
---

# Project Planning Documentation

## Overview

Create and optimize large-scale project planning documentation for complex software projects. Covers milestone decomposition, dependency chain analysis, multi-level step guides, impact analysis, rollback plans, and multi-perspective validation (user/developer/manager).

This skill governs **project-level planning documents** (milestones, phases, iterations, risk matrices). It is NOT for implementation plans (use `writing-plans`) or session tracking (use `planning-with-files`).

## When to Use

**Use when:**
- Planning a multi-milestone project (3+ milestones, 20+ tasks)
- Optimizing existing planning documents for completeness
- Creating dependency chain analysis across modules
- Writing rollback strategies for project phases
- Performing multi-perspective validation (user/developer/manager)
- The user asks for "规划" (planning), "执行方案" (execution plan), or "任务清单" (task list) for a large project

**Don't use when:**
- Writing a single-feature implementation plan (use `writing-plans`)
- Tracking progress within a single session (use `planning-with-files`)
- Simple task breakdown with <5 steps

## Document Hierarchy

Large projects use a 3-tier document structure:

```
.docs/Parses/
├── plans.md              # Master plan (milestone overview, dependency graph, iteration schedule)
├── todolists.md          # Task清单 (all tasks with priority, module, impact, status)
├── M{N}-*.md             # Milestone-level plans (phase overview, execution order, rollback)
├── P{N}.{X}-*.md         # Phase-level plans (task details, multi-level steps, verification)
└── 优化索引.md            # Optimization index (change log, file structure, execution advice)
```

### Tier Responsibilities

| Tier | File | Content | Audience |
|------|------|---------|----------|
| Master | `plans.md` | Milestone overview, dependency graph, iteration schedule, risk matrix, competitor comparison | All stakeholders |
| Task list | `todolists.md` | Every task with priority, module, impact, dependency, status | Developers |
| Milestone | `M{N}-*.md` | Phase overview, execution order, multi-level steps for key phases, rollback | Team leads |
| Phase | `P{N}.{X}-*.md` | Task details, step-by-step guide, verification, confidence | Implementers |

## Required Sections

### plans.md (Master Plan)

```markdown
# [Project] 逐步优化执行方案

> **基础**: [base project/version] | **生成日期**: [date] | **置信度**: 100%
> **核心原则**: 业务完整 · 架构最优 · 性能最佳

## 目录
- [一、执行总览](#一执行总览)
- [二、Milestone 规划详情](#二milestone-规划详情)
- [三、全局依赖链](#三全局依赖链)
- [四、迭代执行计划（含多级步骤）](#四迭代执行计划含多级步骤)
- [五、风险评估与回滚方案](#五风险评估与回滚方案)
- [六、三重视角验证](#六三重视角验证)
- [七、竞品对比验证](#七竞品对比验证)
- [八、任务统计总览](#八任务统计总览)
- [九、引用文档索引](#九引用文档索引)
```

### Milestone Table Format

| # | Milestone | 优先级 | Phases | 任务数 | 预估工时 | 依赖 | 回滚策略 |
|---|-----------|--------|--------|--------|---------|------|---------|
| M1 | Name | P0 | 7 | 19 | 8 天 | 无 | 配置回滚 |

### Dependency Chain Format

Use ASCII art for dependency graphs:
```
M1(全局) ──────────┬─→ M3(文件) ──→ M11(性能)
  │                │
  ├────────────────┼─→ M4(知识库) ──→ M8(文档流)
```

### todolists.md (Task List)

Each Phase section uses a table:

| # | Task | 涉及模块 | 优先级 | 不良影响 | 状态 |
|---|------|---------|--------|---------|------|
| 1.1.1 | Description | `path/to/file.py` | P0 | Impact description | ⬜ |

Include appendices:
- 附录A: 已验证源码现状 (verified source code status)
- 附录B: 待验证/待修复项 (pending items)
- 附录C: 执行顺序与迭代规划 (execution order)
- 附录D: 风险评估 (risk assessment)
- 附录E: 任务统计总览 (task statistics)

### P-phase Files (Phase Detail)

Each phase file MUST include:

```markdown
# P{N}.{X} [Phase Name]

> **Milestone**: M{N} | **优先级**: P{level} | **状态**: ⬜
> **任务数**: N | **预估工时**: N 天
> **需求来源**: [source document]
> **依赖**: [dependencies] | **回滚**: [rollback strategy]

## 目录
- [1. 任务总览](#1-任务总览)
- [2. 执行顺序与依赖](#2-执行顺序与依赖)
- [3. Task {N}.{X}.{Y}: [Task Name]](#3-task-)
  - 3.1 需求来源
  - 3.2 问题现状
  - 3.3 操作步骤目录
  - 3.4 先做什么
  - 3.5 后做什么
  - 3.6 怎么做（多级步骤）
  - 3.7 涉及模块
  - 3.8 不良影响
  - 3.9 验证方法
  - 3.10 置信度
- [4. 不良影响分析](#4-不良影响分析)
- [5. 回滚方案](#5-回滚方案)
- [6. 三重视角验证](#6-三重视角验证)
```

## Multi-Level Step Guide Format

Steps must be decomposed to 3 levels:

```markdown
### Phase 2.5: Provider Configuration (1 day)

#### Step 1: DeerAPI Model List Correction (2.5.3)
- **1.1** Read `conf/llm_factories.json` DeerAPI section
- **1.2** Compare with AGENTS.md DeerAPI initial model list (7 Chat models)
- **1.3** Replace model list, remove old prefix format
- **1.4** Verify `tags` field contains `TEXT`
- **1.5** Test: frontend shows 7 Chat models
- **涉及文件**: `conf/llm_factories.json`
- **不良影响**: Replaces model list, existing users unaffected
- **回滚**: Restore original JSON content
```

**Rule**: Each sub-step (1.1, 1.2, etc.) must be a single atomic action.

## Impact Analysis Table

| 操作 | 影响范围 | 严重程度 | 缓解措施 |
|------|---------|---------|---------|
| Model list replacement | New user available models | 🟡 Medium | llm_factories.json only affects new users |

Severity levels: 🟢 Low, 🟡 Medium, 🔴 High

## Rollback Plan Format

Each operation needs a rollback plan:

| Milestone | 回滚策略 | 回滚步骤 | 回滚时间 | 数据影响 |
|-----------|---------|---------|---------|---------|
| M2 模型 | JSON回滚 | 1. Restore JSON 2. Restart backend | 3分钟 | 无 |

Rollback strategy types:
- **配置回滚** (config rollback): Restore config files, restart
- **JSON回滚** (JSON rollback): Restore JSON config
- **前端回滚** (frontend rollback): Git revert + rebuild
- **功能开关** (feature toggle): Disable feature flag
- **默认值回滚** (default value rollback): Restore default values
- **参数回滚** (parameter rollback): Restore performance parameters
- **全量重建** (full rebuild): Rebuild index/data

## Three-Perspective Validation

Every milestone and phase must include:

### 使用者视角 (User Perspective)
- 体验提升 (experience improvement): description
- Star rating: ⭐⭐⭐⭐⭐
- 回滚影响 (rollback impact): description

### 参与者视角 (Developer Perspective)
- 开发难度 (development difficulty): 低/中/高
- 影响范围 (impact scope): description
- 测试复杂度 (test complexity): 低/中/高
- 回滚难度 (rollback difficulty): 低/中/高

### 管理者视角 (Manager Perspective)
- 管理价值 (management value): star rating
- 运维影响 (operations impact): description
- 回滚成本 (rollback cost): 低/中/高

## Priority Classification

| Priority | Percentage | Description | Execution Window |
|----------|-----------|-------------|-----------------|
| P0 | ~27% | Must fix within 1-2 weeks | Iteration 1-2 |
| P1 | ~37% | Important experience/management enhancement | Iteration 3-4 |
| P2 | ~36% | Long-term optimization/architecture change | Iteration 5+ |

## Optimization Checklist

When optimizing existing planning documents, verify:

- [ ] Each task has multi-level step guide (3 levels minimum)
- [ ] Each task has operation step directory (numbered)
- [ ] Dependency chain diagram exists (ASCII art)
- [ ] Impact analysis table exists per phase
- [ ] Rollback plan exists per operation
- [ ] Verification checkpoint exists per task
- [ ] Three-perspective validation exists per milestone/phase
- [ ] Competitor comparison exists in master plan
- [ ] Risk assessment matrix exists
- [ ] Task statistics summary exists
- [ ] No duplicate tasks across phases
- [ ] All file paths are specific (not vague references)
- [ ] Confidence level stated (must be 100%)

## Common Pitfalls

### Vague Task Descriptions
**Bad:** "Add authentication"
**Good:** "Create User model with email and password_hash fields in `api/db/db_models.py`"

### Missing Dependency Chains
Always show what must be done first and what can be parallelized.

### No Rollback Plan
Every operation that modifies data, config, or behavior needs a rollback strategy with estimated time.

### Single-Perspective Analysis
Always validate from user, developer, AND manager perspectives.

### Missing Verification Steps
Each task must have concrete verification steps (not "test it works").

### Overly Large Phase Files
Phase files should focus on their specific phase. Cross-reference other phases instead of duplicating content.

### Insufficient Step Decomposition
Steps must be decomposed to atomic actions. If a step requires more than one tool call or one file edit, decompose further.

## Principles

1. **业务完整** (Business completeness): Every user requirement must map to at least one task
2. **架构最优** (Optimal architecture): Changes should follow existing architecture patterns
3. **性能最佳** (Best performance): Consider performance impact of every change
4. **基于事实辩证** (Fact-based dialectic): Verify every claim against source code
5. **假设性求证** (Hypothesis verification): Question assumptions, verify independently
6. **三重视角** (Three perspectives): User, developer, manager
7. **100%置信度** (100% confidence): All plans must be verifiable against source code

## Related Skills

- `software-development/writing-plans` — For single-feature implementation plans with TDD
- `openclaw-imports/planning-with-files` — For session-level task tracking
- `openclaw-imports/executing-plans` — For executing written plans

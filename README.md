# AideanAgentFleet

> **为“一人公司”打造的 AI Agent 执行控制平面。**
>
> 不是再造一个 Agent，而是让一个人能够可靠地组织、调度、验证和管理一支由不同 AI Agent 组成的“数字员工团队”。

[![Status](https://img.shields.io/badge/status-design--phase-blue)](#)
[![License](https://img.shields.io/badge/license-TBD-lightgrey)](#)
[![Target](https://img.shields.io/badge/target-One--Person--Company-purple)](#)

---

## 为什么需要 AideanAgentFleet？

OpenClaw、Hermes 等项目正在越来越擅长：

> **让一个 Agent 长期替你工作。**

这恰恰意味着，我们没有必要再做一个 Agent。

真正值得解决的问题是：

> **当一个人同时拥有多个不同能力、不同模型、不同工具的 Agent 时，如何让它们可靠地协同完成一个复杂工程？**

一个“一人公司”真正缺少的，不是更多聊天机器人，而是一个能够替自己管理 AI 员工的**执行控制系统**。

AideanAgentFleet 的目标，就是成为这个系统。

```text
                 一个人
                    │
                    ▼
          ┌──────────────────┐
          │   AI 组织 / GSD   │
          │  规划 · 拆解 · 分工 │
          └────────┬─────────┘
                   │ TaskPack
                   ▼
        ┌────────────────────────┐
        │    AideanAgentFleet    │
        │   AI Agent 执行控制平面 │
        ├────────────────────────┤
        │ DAG / Scheduler        │
        │ Policy Engine          │
        │ Resource Lease         │
        │ Worktree Isolation     │
        │ Machine Gate           │
        │ Evidence               │
        │ Semantic Verifier      │
        │ Event / State          │
        └───────────┬────────────┘
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
        Codex    Claude     OpenCode
        Hermes    Pi        Other Agents
          │         │         │
          └─────────┼─────────┘
                    ▼
             实际项目 / 产品
```

---

# 核心定位

## AideanAgentFleet ≠ Agent

AideanAgentFleet 不负责成为“最聪明的 Agent”。

它负责：

- **谁来做**
- **做什么**
- **什么时候做**
- **能不能并行**
- **能修改什么**
- **不能修改什么**
- **失败怎么办**
- **如何自动重试**
- **什么时候重新分配**
- **到底有没有真正完成**
- **如何留下完整证据**
- **什么时候必须交给人**

因此：

> **Agent 是可替换的。**
>
> **AideanAgentFleet 的执行协议才是核心资产。**

---

# 五个核心价值

## 1. Machine Gate：Agent 说完成，不等于真的完成

传统 AI Coding Agent 的典型流程：

```text
Agent
  │
  ├─ 写代码
  ├─ 跑测试
  └─ “已完成”
       │
       ▼
     人检查
```

AideanAgentFleet：

```text
Agent 报告完成
      │
      ▼
┌─────────────────────┐
│     Machine Gate    │
├─────────────────────┤
│ Diff Gate           │
│ Path Gate           │
│ Port Gate           │
│ Command/Test Gate   │
│ Contract Gate       │
└──────────┬──────────┘
           ▼
   Semantic Verifier
           │
      ┌────┴────┐
      ▼         ▼
    PASS       FAIL
                │
                ▼
             REWORK
```

核心原则：

> **Machine Gate > Agent Self-Report**

系统以真实代码、真实命令输出、真实测试结果和真实资源状态作为事实依据，而不是相信 Agent 自己说“完成了”。

---

## 2. Policy Engine：把失败变成可执行的恢复策略

AI Agent 在真实环境中必然会失败：

- API 429
- 模型不可用
- 上下文过长
- 执行超时
- 测试失败
- 资源冲突
- 端口被占用
- 修改越权
- 任务范围过大

AideanAgentFleet 不把这些问题简单处理成：

> “再让 Agent 试一次。”

而是通过确定性的 Policy Engine 进行恢复：

```text
429
 │
 ├─ Fallback Model
 │
 ├─ Backoff
 │
 ├─ Serialize
 │
 └─ Escalate

Timeout
 │
 └─ Split / Retry

Machine Gate Failed
 │
 └─ Retry Context → Rework → Re-Gate

Retry Exhausted
 │
 └─ ESCALATED
```

核心思想：

> **LLM 负责判断复杂问题，Policy Engine 负责确定性地执行恢复。**

---

## 3. Resource Lease + Worktree：让多个 Agent 真正安全并行

多个 Agent 同时工作时，最危险的不是“不会写代码”，而是**互相破坏工作空间**。

例如：

```text
A → Backend
B → Frontend
C → Tests
```

A 占用：

```text
src/backend/**
```

B 占用：

```text
src/frontend/**
```

C 占用：

```text
tests/**
```

AideanAgentFleet 通过：

- Resource Lease
- Worktree Isolation
- Write Scope
- Conflict Precheck
- Port Lease

控制 Agent 的资源边界。

如果 D 试图同时修改已经被 A 占用的核心区域：

```text
D → src/backend/**
         │
         ▼
    Resource Conflict
         │
         ▼
       BLOCKED
```

而不是让两个 Agent 同时修改同一片代码。

---

## 4. Evidence：每一个结论都有证据链

AideanAgentFleet 不希望最终报告只是：

> “AI 员工完成了任务。”

而是：

```text
Task #A-003

Status:
SUCCEEDED

Diff:
✓

Path:
✓

Port:
✓

Command:
npm test

Exit Code:
0

Evidence:
artifacts/A-003/test.log

Semantic Verification:
PASS
```

系统采用：

```text
Raw Evidence
      │
      ▼
Machine Facts
      │
      ▼
Semantic Verification
      │
      ▼
Final Report
```

核心原则：

> **先保存事实，再生成结论。**

因此可以回答：

- Agent 做了什么？
- 修改了哪些文件？
- 执行了什么命令？
- 测试是否真的通过？
- 为什么被拒绝？
- 为什么触发重工？
- 重工了几次？
- 最终是谁完成的？
- 哪一步出现了异常？

---

## 5. Event + State：可恢复、可审计，而不是“一次性脚本”

AideanAgentFleet 不把一次执行看成一个黑盒进程。

核心状态与事件持久化：

```text
Task
 │
 ▼
PENDING
 │
 ▼
READY
 │
 ▼
RUNNING
 │
 ▼
VERIFYING
 │
 ├───────────────┐
 ▼               ▼
SUCCEEDED       FAILED
                 │
                 ▼
             RETRY_WAIT
                 │
                 ▼
              RUNNING
                 │
                 ▼
             ESCALATED
```

事件与状态独立保存：

```text
SQLite
  └─ 当前状态 / Projection

events.jsonl
  └─ Append-only Event Log

artifacts/
  └─ 原始证据 / 执行产物

reports/
  └─ 最终报告
```

因此：

> **电脑重启，不应该意味着整个 AI 团队失忆。**

系统可以从 checkpoint 恢复执行。

---

# 与 OpenClaw / Hermes 的区别

AideanAgentFleet 不与 OpenClaw / Hermes 竞争“谁是更好的 Agent”。

它们解决的问题不同。

| | OpenClaw / Hermes | AideanAgentFleet |
|---|---|---|
| 核心问题 | 让 Agent 长期替你工作 | 让多个 Agent 可靠完成复杂工程 |
| 定位 | Agent / Assistant Runtime | Agent Execution Control Plane |
| Memory | 核心能力 | 非核心 |
| Skills | 核心能力 | 通过 Worker / Domain 接入 |
| Chat / Channel | 核心能力 | 非核心 |
| 单 Agent 长任务 | 强 | 支持 |
| 多 Agent 编排 | 支持 | 核心 |
| DAG | 辅助 | 核心 |
| Resource Lease | 非核心 | 核心 |
| Worktree Isolation | 非核心 | 核心 |
| Machine Gate | 非核心 | 核心 |
| Evidence Chain | 非核心 | 核心 |
| Deterministic Recovery | 非核心 | 核心 |
| Event Sourcing | 非核心 | 核心 |
| Agent 替换 | 支持不同 Agent | 核心设计 |
| 一人公司 AI 员工管理 | 间接 | **核心目标** |

因此：

> **OpenClaw / Hermes 可以是 AideanAgentFleet 的 Agent Worker。**

未来完全可以：

```yaml
workers:
  frontend:
    adapter: claude-code

  backend:
    adapter: codex

  testing:
    adapter: opencode

  general:
    adapter: hermes
```

甚至：

```text
OpenClaw
   │
   ▼
AideanAgentFleet
   │
   ├── Codex
   ├── Claude Code
   ├── OpenCode
   ├── Hermes
   ├── Pi
   └── Other Agents
```

**竞争关系 → 生态关系。**

---

# GSD / 三省六部应该放在哪里？

AideanAgentFleet 不需要重新发明“AI 如何思考”。

可以将 GSD / 三省六部类机制作为上层的**AI 组织层**：

```text
                  User
                    │
                    ▼
          ┌──────────────────┐
          │ OpenClaw / Hermes │
          │   Resident Agent  │
          └────────┬─────────┘
                   ▼
          ┌──────────────────┐
          │ AI Organization  │
          │                  │
          │ GSD / 三省六部    │
          │ 规划 / 审核 / 分工 │
          └────────┬─────────┘
                   │
                TaskPack
                   ▼
        ┌──────────────────────┐
        │  AideanAgentFleet    │
        │ Execution Control    │
        └──────────┬───────────┘
                   ▼
             Agent Workers
```

可以形成清晰分工：

### AI 组织层

负责：

- 理解目标
- 制定方案
- 拆解任务
- 分配角色
- 调整任务
- 语义审核
- 生成 TaskPack

### AideanAgentFleet

负责：

- DAG
- Scheduler
- State
- Event
- Lease
- Worktree
- Policy
- Machine Gate
- Evidence
- Recovery
- Report

核心边界：

> **LLM 可以提出决策，但不能直接改变事实。**

---

# 为“一人公司”服务

传统公司需要：

```text
产品经理
设计师
前端
后端
测试
运维
项目经理
```

一人公司无法长期承担这样的组织成本。

AideanAgentFleet 的目标不是让一个人“同时操作十几个 AI”。

而是：

> **让一个人管理 AI 员工，而不是管理 AI 工具。**

理想状态：

```text
              一个人
                 │
          “完成这个项目”
                 │
                 ▼
       AI Organization
                 │
           自动拆解任务
                 │
                 ▼
       AideanAgentFleet
                 │
        ┌────────┼────────┐
        ▼        ▼        ▼
      Agent A  Agent B  Agent C
        │        │        │
      Backend  Frontend  Test
        │        │        │
        └────────┼────────┘
                 ▼
          Machine Gate
                 │
        ┌────────┴────────┐
        ▼                 ▼
      PASS              FAIL
                          │
                          ▼
                    自动重工 / 恢复
                          │
                          ▼
                       PASS
                 │
                 ▼
              Final Report
```

人只需要处理：

```text
需要人类判断的问题
不可逆操作
预算 / 权限决策
自动恢复失败后的 ESCALATED
```

而不是参与每一个普通开发步骤。

---

# 核心架构

```text
┌──────────────────────────────────────────────────────┐
│                    AI Organization                   │
│              GSD / 三省六部 / Manager                │
└──────────────────────────┬───────────────────────────┘
                           │ TaskPack
                           ▼
┌──────────────────────────────────────────────────────┐
│                 AideanAgentFleet                     │
│                                                      │
│  ┌─────────────┐   ┌──────────────┐                 │
│  │ Workflow    │   │ Scheduler    │                 │
│  └─────────────┘   └──────────────┘                 │
│                                                      │
│  ┌─────────────┐   ┌──────────────┐                 │
│  │ Policy      │   │ Resource     │                 │
│  │ Engine      │   │ Manager      │                 │
│  └─────────────┘   └──────────────┘                 │
│                                                      │
│  ┌─────────────┐   ┌──────────────┐                 │
│  │ Gate Engine │   │ Evidence     │                 │
│  └─────────────┘   └──────────────┘                 │
│                                                      │
│  ┌─────────────┐   ┌──────────────┐                 │
│  │ Event Bus   │   │ State Store  │                 │
│  └─────────────┘   └──────────────┘                 │
└──────────────────────────┬───────────────────────────┘
                           │
                 Worker Adapter Layer
                           │
       ┌───────────────────┼───────────────────┐
       ▼                   ▼                   ▼
 ┌──────────┐        ┌──────────┐        ┌──────────┐
 │ Claude   │        │ Codex    │        │ OpenCode │
 │ Code     │        │          │        │          │
 └──────────┘        └──────────┘        └──────────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           ▼
                  Actual Project
```

---

# 核心设计原则

### 01 — Agent 可替换

不绑定某一家模型或 Agent。

```text
Claude Code
Codex
OpenCode
Hermes
Pi
Other Agent
```

都只是 Worker。

---

### 02 — Machine Gate 高于 Agent 自报

```text
Agent says PASS
       ≠
System PASS
```

最终事实必须来自机器证据。

---

### 03 — LLM 与确定性控制分离

```text
LLM
 └─ 负责复杂判断

Kernel
 └─ 负责确定性执行
```

不让 LLM 决定：

- 是否允许写某目录
- 是否占用某资源
- 是否允许两个任务并行
- 是否超过重试次数
- 是否满足机器测试
- 是否违反端口约束

---

### 04 — 失败是一等公民

失败不是异常情况，而是系统正常状态。

```text
FAILED
BLOCKED
RETRY_WAIT
ESCALATED
CANCELLED
```

都应该被明确建模。

---

### 05 — Evidence First

所有最终结论都尽量能够追溯到：

```text
Command
Diff
Test
Event
Artifact
Resource State
```

---

### 06 — Kernel 与 Domain 解耦

当前：

```text
Coding Domain
```

未来可以扩展：

```text
Coding
Media
Research
Content
Automation
Data
```

而不改变核心执行协议：

```text
TaskPack
Event
Gate
Lease
Evidence
Policy
```

---

# MVP

第一阶段聚焦 Coding Domain。

### 支持

- [ ] `fleet.yaml`
- [ ] TaskPack
- [ ] DAG Workflow
- [ ] Scheduler
- [ ] Claude Code Adapter
- [ ] Codex Adapter
- [ ] OpenCode Adapter
- [ ] Pi Adapter
- [ ] Policy Engine
- [ ] Machine Gates
- [ ] Semantic Verifier
- [ ] Worktree Isolation
- [ ] Resource Lease
- [ ] Port Lease
- [ ] SQLite State Store
- [ ] JSONL Event Log
- [ ] Artifact Store
- [ ] HTML Report
- [ ] Resume / Checkpoint
- [ ] Streamlit UI

---

# 一次完整执行

```text
1. 用户准备需求 / TaskPack
          ↓
2. AI Organization 规划
          ↓
3. AideanAgentFleet 静态检查
          ↓
4. 构建 DAG
          ↓
5. 检查资源冲突
          ↓
6. 创建 Worktree / Lease
          ↓
7. 并行启动 Agent
          ↓
8. Agent 执行
          ↓
9. 收集 Evidence
          ↓
10. Machine Gate
          ↓
11. Semantic Verify
          │
      ┌───┴───┐
      ▼       ▼
     PASS    FAIL
      │       │
      │       ▼
      │   Policy Engine
      │       │
      │   Retry / Rework
      │       │
      │       └──────→ Gate
      │
      ▼
12. Merge
      ↓
13. Final Verification
      ↓
14. Report
      ↓
15. 完成
```

---

# 一个重要的工程原则

AideanAgentFleet 不追求：

> **让所有事情都自动化。**

而追求：

> **自动化所有能够可靠自动化的事情，并把无法可靠判断的问题自动升级给人。**

因此最终状态不只有：

```text
SUCCESS
```

还有：

```text
FAILED
BLOCKED
ESCALATED
CANCELLED
```

这使系统能够在“自动化”和“安全性”之间保持边界。

---

# 与“一人公司”的最终关系

AideanAgentFleet 的终极目标不是：

> “让 AI 替你写更多代码。”

而是：

> **让一个人拥有一支可以被可靠管理的 AI 数字员工团队。**

未来，一个人可以拥有：

```text
1 Human
   │
   ├── AI Product Manager
   ├── AI Architect
   ├── AI UI Designer
   ├── AI Frontend Engineer
   ├── AI Backend Engineer
   ├── AI QA Engineer
   ├── AI DevOps Engineer
   └── AI Researcher
```

这些 Agent 可以来自完全不同的：

```text
Models
Providers
Coding Agents
Open-source Agents
Local Agents
Cloud Agents
```

而 AideanAgentFleet 负责把它们统一成：

> **一支可调度、可验证、可恢复、可审计的 AI Workforce。**

---

# Roadmap

## Phase 1 — Coding MVP

建立可靠的执行控制平面：

```text
TaskPack
DAG
Worker
Scheduler
Gate
Evidence
Policy
Lease
Worktree
Event
State
Report
```

## Phase 2 — AI Organization

接入：

```text
GSD
三省六部
Manager Agent
```

让任务从：

```text
Goal
```

自动生成：

```text
TaskPack
```

## Phase 3 — More Agents

扩展 Worker Adapter：

```text
Claude Code
Codex
OpenCode
Hermes
OpenClaw
Pi
Other Agents
```

## Phase 4 — More Domains

从 Coding 扩展到：

```text
Media
Research
Content
Automation
Data
```

核心 Kernel 不变。

---

# 设计哲学

```text
        更聪明的 Agent
              │
              ▼
       解决“能不能做”
              │
              │
              ▼
     AideanAgentFleet
              │
              ▼
       解决“怎么可靠地做”
              │
       ┌──────┼──────┐
       ▼      ▼      ▼
     调度    验证    恢复
       │      │      │
       └──────┼──────┘
              ▼
          一人公司
```

> **Agent 决定能力上限。**
>
> **AideanAgentFleet 决定这些能力能否被组织成稳定的生产力。**

---

## 项目愿景

**让一个人，不再只是“使用 AI 工具”。**

而是：

> **拥有、管理并运营一支 AI 数字员工团队。**

---

## Status

🚧 **Early Development / Architecture & MVP**

当前首先验证 Coding Domain 的：

1. 多 Agent 并行执行
2. TaskPack 驱动
3. Machine Gate
4. Evidence Chain
5. 自动重工与恢复
6. Worktree / Resource 隔离
7. Checkpoint Resume
8. 最终事实报告

---

## License

TBD

---

<p align="center">
  <strong>AideanAgentFleet</strong><br>
  One Human. Many Agents. One Reliable Execution Plane.
</p>

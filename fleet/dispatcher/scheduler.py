# -*- coding: utf-8 -*-
"""Persistent scheduler skeleton: DAG + lease + heartbeat + reclaim.

This stage only lands the data structure and pure rules so later stages can
persist to SQLite without changing callers. No threads, no network, no CLI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


TERMINAL = {"DONE", "PARTIAL", "BLOCKED", "FAILED"}


@dataclass
class TaskNode:
    id: str
    after: List[str] = field(default_factory=list)
    state: str = "DRAFT"
    lease_owner: str = ""
    lease_until: float = 0.0
    heartbeat_at: float = 0.0
    attempts: int = 0
    consecutive_failures: int = 0


def dependency_blockers(node: TaskNode, states: Dict[str, str]) -> List[str]:
    missing = []
    for dep in node.after or []:
        if states.get(dep) not in ("DONE", "PARTIAL"):
            missing.append(dep)
    return missing


def can_claim(node: TaskNode, states: Dict[str, str], now: float) -> tuple[bool, str]:
    if node.state in TERMINAL:
        return False, f"terminal state {node.state}"
    if dependency_blockers(node, states):
        return False, "dependency not satisfied: " + ",".join(dependency_blockers(node, states))
    if node.lease_owner and node.lease_until > now:
        return False, f"leased by {node.lease_owner}"
    return True, "claimable"


def should_reclaim(node: TaskNode, now: float) -> bool:
    return bool(node.lease_owner) and node.lease_until <= now and node.state not in TERMINAL


def record_failure(node: TaskNode, max_failures: int = 3) -> str:
    node.attempts += 1
    node.consecutive_failures += 1
    if node.consecutive_failures >= max_failures:
        node.state = "BLOCKED"
        return "BLOCKED"
    node.state = "READY"
    return "READY"


# ---- ready wave（推荐波）：纯函数，无副作用 ------------------------------------

# 可派工状态（与 console 9 态口径兼容）
DISPATCHABLE_STATES = {"DRAFT", "REWORK"}
# 角色在途状态：命中即视为该角色占用（每角色 1 并发）
IN_FLIGHT_STATES = {"ASSIGNED", "DOING", "SUBMITTED", "REVIEWING"}
# 前置满足判定：与 dependency_blockers / console dispatch_dependency_blockers 一致
DEP_SATISFIED = ("DONE", "PARTIAL")
# 推荐时忽略的在途状态：SUBMITTED/REVIEWING 的产物已交付、角色实际空闲，
# 仍作为 blocker 展示（提示"已有交付"）；ASSIGNED/DOING 则直接顶格拦截。
SHOW_IN_FLIGHT_STATES = IN_FLIGHT_STATES | {"SUBMITTED", "REVIEWING"}


def topological_ready(tasks):
    """给定任务快照，算出推荐波（ready wave）。

    tasks: {task_id: {"state": str, "after": [dep_id, ...], "assignee": str, ...}}
    返回 (ready, blocked, invalid)：
      ready    —— 可派任务 id 列表：自身 ∈ DISPATCHABLE_STATES 且全部 after 满足；
                  同角色互斥——该角色已有在途（IN_FLIGHT_STATES）任务时候选剔除进 blocked。
      blocked  —— {task_id: 原因说明}（前置未满足 / 角色在途）
      invalid  —— [task_id, ...]：after 引用了不存在的任务 id，或处于依赖环中
    """
    ids = set(tasks)
    by_state = {tid: (t or {}).get("state", "MISSING") for tid, t in tasks.items()}

    # 1) 脏引用：after 指向不存在的任务 id
    invalid = set()
    for tid, t in tasks.items():
        for dep in (t or {}).get("after") or []:
            if dep not in ids:
                invalid.add(tid)
                break

    # 2) 循环依赖：迭代「可达脏/环集合」传播，直到不动点。
    # 每轮：(b) 扫描所有 after 边，若 dep 在 dirty 中则 tid 也进 dirty；
    #       (c) 对剩余干净子图做 DFS 环检测（push-time 检查：
    #           dep 已在当前 DFS 栈 = 环；环成员 = 栈中从 dep 到栈顶的节点），
    #           环成员也进 dirty。处理顺序不敏感，多轮直到收敛。
    dirty = set(invalid)  # 步骤 1 已识别的脏引用节点
    while True:
        before = len(dirty)
        # b) 可达脏传播
        for tid in ids:
            if tid in dirty:
                continue
            for dep in (tasks.get(tid) or {}).get("after") or []:
                if dep in dirty:
                    dirty.add(tid)
                    break
        # c) 剩余干净子图上的环检测（push-time DFS）
        remaining = sorted(ids - dirty)
        done: set = set()  # 已确证无环的节点
        for start in remaining:
            if start in dirty or start in done:
                continue
            stack: List[str] = [start]
            pos: Dict[str, int] = {start: 0}  # tid -> 在 stack 中的索引
            while stack:
                tid = stack[-1]
                advanced = False
                # 找 tid 的下一个未处理 dep
                for dep in (tasks.get(tid) or {}).get("after") or []:
                    if dep not in ids or dep in dirty or dep in done:
                        continue
                    if dep in pos:
                        # dep 已在栈中 → 环！环成员 = 栈中从 dep 到栈顶
                        for x in list(stack[pos[dep]:]):
                            dirty.add(x)
                        stack = []
                        break
                    # 前进：push dep
                    pos[dep] = len(stack)
                    stack.append(dep)
                    advanced = True
                    break
                if not stack:
                    break  # 环已检出，本次 DFS 作废
                if advanced:
                    continue  # 深入新 push 的节点
                # tid 的所有 dep 已处理完 → 完成，回溯
                del pos[tid]
                done.add(tid)
                stack.pop()
        if len(dirty) == before:
            break
    invalid = dirty

    # 3) 前置满足 + 角色在途
    # 顶格拦截：角色有 ASSIGNED/DOING 任务（实际占用）→ 候选剔除
    busy_roles = {
        (t or {}).get("assignee")
        for t in tasks.values()
        if (t or {}).get("state") in ("ASSIGNED", "DOING") and (t or {}).get("assignee")
    }
    # 展示层：SUBMITTED/REVIEWING 也计入「在途展示」，但只作为 blocker 提示、不顶格拦截
    show_roles = {
        (t or {}).get("assignee")
        for t in tasks.values()
        if (t or {}).get("state") in SHOW_IN_FLIGHT_STATES and (t or {}).get("assignee")
    }
    ready: List[str] = []
    blocked: Dict[str, str] = {}
    for tid in sorted(tasks, key=str):
        t = tasks.get(tid) or {}
        if tid in invalid:
            continue
        st = by_state[tid]
        if st not in DISPATCHABLE_STATES:
            continue  # 在途/终态任务既不可派也不是 blocker
        missing = [d for d in (t.get("after") or [])
                   if by_state.get(d) not in DEP_SATISFIED and d in ids]
        if missing:
            blocked[tid] = "前置未满足:" + ",".join(
                f"{d}={by_state.get(d, 'MISSING')}" for d in missing)
            continue
        if t.get("assignee") in busy_roles:
            blocked[tid] = f"角色在途:{t.get('assignee')}"
            continue
        if t.get("assignee") in show_roles:
            blocked[tid] = f"角色已有交付:{t.get('assignee')}（SUBMITTED/REVIEWING，不顶格拦截）"
            continue
        ready.append(tid)
    # 4) 脏引用任务进 invalid 列表，不进 blocked（依赖数据本身有问题，需人工修）
    for tid in invalid:
        blocked.pop(tid, None)
    return ready, blocked, sorted(invalid)

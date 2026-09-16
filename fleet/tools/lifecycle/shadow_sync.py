# -*- coding: utf-8 -*-
"""R7/R9: SQLite 双写与恢复看门狗（先影子运行，不切换读源）。"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path("E:/Code/AideanCompany")
sys.path.insert(0, str(ROOT / "fleet" / "console"))
sys.path.insert(0, str(ROOT / "fleet" / "dispatcher"))

from storage import init_db, DB_PATH  # noqa: E402


def snapshot_tasks(tasks_file: Path) -> int:
    """把 tasks.json 影子同步进 fleet.db（幂等 upsert），返回条数。不改动 tasks.json。"""
    data = json.loads(tasks_file.read_text(encoding="utf-8"))
    init_db(DB_PATH)
    conn = sqlite3.connect(str(DB_PATH))
    n = 0
    try:
        for t in data["tasks"]:
            conn.execute(
                "INSERT INTO tasks(id,pid,title,state,assignee,reviewer,workspace,verify_cmd,payload,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET state=excluded.state, title=excluded.title, "
                "payload=excluded.payload, updated_at=excluded.updated_at",
                (t["id"], t.get("project", ""), t.get("title", ""), t.get("state", "DRAFT"),
                 t.get("assignee", ""), t.get("reviewer", ""), t.get("workspace", ""),
                 t.get("verify_cmd", ""), json.dumps(t, ensure_ascii=False),
                 time.strftime("%Y-%m-%d %H:%M:%S")))
            n += 1
        conn.commit()
    finally:
        conn.close()
    return n


def count_tasks() -> int:
    conn = sqlite3.connect(str(DB_PATH))
    try:
        return conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    finally:
        conn.close()


def reclaim_expired(now_ts: float | None = None) -> list[str]:
    """崩溃恢复：过期 lease 的任务标记 READY 交给调度器（影子逻辑，不动 tasks.json）。"""
    from scheduler import TaskNode, can_claim, should_reclaim
    now_ts = now_ts or time.time()
    conn = sqlite3.connect(str(DB_PATH))
    reclaimed = []
    try:
        rows = conn.execute("SELECT task_id, owner, until FROM leases").fetchall()
        for task_id, owner, until in rows:
            until_ts = _parse(until)
            if until_ts and until_ts <= now_ts:
                conn.execute("DELETE FROM leases WHERE task_id=?", (task_id,))
                reclaimed.append(task_id)
        conn.commit()
    finally:
        conn.close()
    return reclaimed


def _parse(s: str) -> float | None:
    try:
        from datetime import datetime
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").timestamp()
    except Exception:
        return None


if __name__ == "__main__":
    n = snapshot_tasks(ROOT / "fleet" / "console" / "state" / "tasks.json")
    print(json.dumps({"shadow_sync": n, "db": str(DB_PATH), "count": count_tasks()},
                     ensure_ascii=False))

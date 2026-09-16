# -*- coding: utf-8 -*-
"""SQLite queue schema (R4). Real migration runs later; this file fixes the shape."""
from __future__ import annotations

from pathlib import Path
import sqlite3

DB_PATH = Path("E:/Code/AideanCompany/fleet/state/fleet.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects(pid TEXT PRIMARY KEY, name TEXT, meta TEXT);
CREATE TABLE IF NOT EXISTS tasks(
  id TEXT PRIMARY KEY, pid TEXT, title TEXT, state TEXT,
  assignee TEXT, reviewer TEXT, workspace TEXT, verify_cmd TEXT,
  payload TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS task_attempts(
  id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT, attempt INTEGER,
  cli TEXT, model TEXT, pid INTEGER, exit_code INTEGER,
  transcript_path TEXT, transcript_sha256 TEXT,
  started_at TEXT, ended_at TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS task_events(
  seq INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, actor TEXT, action TEXT,
  task_id TEXT, pid TEXT, detail TEXT, extra TEXT, prev_hash TEXT, event_hash TEXT);
CREATE TABLE IF NOT EXISTS leases(
  task_id TEXT PRIMARY KEY, owner TEXT, created_at TEXT,
  until TEXT, heartbeat_at TEXT, percent REAL);
CREATE TABLE IF NOT EXISTS evidence(
  id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT, kind TEXT,
  path TEXT, sha256 TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS approvals(
  id TEXT PRIMARY KEY, task_id TEXT, approver TEXT,
  reason TEXT, created_at TEXT);
"""


def init_db(path: Path = DB_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
    return path

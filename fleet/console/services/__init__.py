# -*- coding: utf-8 -*-
"""R6: 鉴权与审计链（最小可用，不破坏现有本机单机流程）。

- FLEET_API_TOKEN：为空=本机模式（沿用旧行为，仅记录 audit 来源）；
  非空=写操作必须 Authorization: Bearer <token>，读操作不受限。
- 审计哈希链：audit() 追加 prev_hash/event_hash；verify_audit_chain() 可检测断链。
"""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

TOKEN_ENV = "FLEET_API_TOKEN"


def bearer_ok(headers: dict, expected: str) -> bool:
    if not expected:
        return True
    auth = ""
    for k, v in (headers or {}).items():
        if str(k).lower() == "authorization":
            auth = str(v)
            break
    return hmac.compare_digest(auth.strip(), f"Bearer {expected}")


def canonical_event(rec: dict) -> str:
    slim = {k: rec.get(k, "") for k in ("ts", "actor", "action", "task", "detail",
                                        "project", "phase", "role", "cli", "model",
                                        "from", "to", "assignee", "reviewer")}
    return json.dumps(slim, ensure_ascii=False, sort_keys=True)


def event_hash(rec: dict, prev_hash: str) -> str:
    return hashlib.sha256((prev_hash + canonical_event(rec)).encode("utf-8")).hexdigest()


def last_hash(audit_file: Path) -> str:
    prev = "GENESIS"
    if audit_file.exists():
        for line in audit_file.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                d = json.loads(line)
                if d.get("event_hash"):
                    prev = str(d["event_hash"])
            except Exception:
                continue
    return prev


def verify_audit_chain(audit_file: Path) -> dict:
    prev = "GENESIS"
    checked = 0
    broken_at = -1
    if audit_file.exists():
        for i, line in enumerate(audit_file.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                broken_at = i
                break
            checked += 1
            if "event_hash" not in d:
                continue  # 旧行：跳过哈希校验，保持向前兼容
            expect = event_hash(d, str(d.get("prev_hash", "")))
            if d.get("prev_hash") != prev or d.get("event_hash") != expect:
                broken_at = i
                break
            prev = str(d["event_hash"])
    return {"checked": checked, "ok": broken_at < 0, "broken_at": broken_at, "tip": prev}

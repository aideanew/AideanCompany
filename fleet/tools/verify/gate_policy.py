# -*- coding: utf-8 -*-
"""P5-P8 gate policy: machine gates, DONE/REVIEW/CLI evidence rules, retry source.

Pure helpers only. No console process changes, no task mutations, no CLI calls.
The console can import these helpers as a compatibility layer while later stages
rebuild routes/services around the same policy.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


DOC_GATE_RE = re.compile(r"^grep:[^:]+/task-package-[^:]+:", re.I)
MODEL_ALIAS_RE = re.compile(r"(agnes|nvidia|sensenova|modelscope|amd|bai|qwen|deepseek)", re.I)
ALLOWED_ROOTS = [
    Path("E:/Demo"),
    Path("E:/Code/AideanCompany/fleet/projects"),
    Path("E:/Code/AideanBot"),
]
TERMINAL_STATES = {"DONE", "PARTIAL", "BLOCKED", "FAILED"}
VALID_STATES = {
    "DRAFT", "READY", "ASSIGNED", "RUNNING", "SUBMITTED", "VERIFYING",
    "REVIEWING", "DONE", "PARTIAL", "REWORK", "BLOCKED", "FAILED",
}


def load_retry_policy(model_pool_path: str | Path) -> dict:
    pool = json.loads(Path(model_pool_path).read_text(encoding="utf-8"))
    retry = dict(pool.get("retry") or {})
    retry.setdefault("interval_seconds", 10)
    retry.setdefault("max_attempts", 10)
    retry.setdefault("backoff_jitter_seconds", 2)
    retry.setdefault("hard_signals", ["401", "402", "403", "model_not_found", "quota_exhausted", "insufficient_credits"])
    return retry


def is_doc_gate_cmd(cmd: str) -> bool:
    return bool(DOC_GATE_RE.match((cmd or "").strip()))


def workspace_allowed(path: str | Path) -> bool:
    p = Path(path).resolve()
    return any(p == root or str(p).lower().startswith(str(root).lower()) for root in ALLOWED_ROOTS)


def evidence_path_present(evidence_root: str | Path, task_id: str) -> bool:
    root = Path(evidence_root)
    return (root / f"{task_id}-cli.log").exists()


def cli_transcript_is_valid(transcript_path: str | Path, assigned_ts: str = "") -> tuple[bool, str]:
    p = Path(transcript_path)
    if not p.exists():
        return False, "missing cli transcript"
    text = p.read_text(encoding="utf-8", errors="replace")
    required = ["[cwd]", "[cli]", "[model]", "[pid]", "[exit]", "[started]", "[ended]"]
    missing = [tag for tag in required if tag not in text]
    if missing:
        return False, "transcript missing machine tags: " + ",".join(missing)
    return True, "transcript valid"


def terminal_gate_reasons(task: dict, assigned_ts: str = "", evidence_root: str | Path | None = None) -> list[str]:
    reasons = []
    if task.get("state") not in TERMINAL_STATES:
        return ["not terminal"]
    if task.get("state") == "DONE":
        if task.get("verify_ok") is not True:
            reasons.append("verify_ok is not True")
        if not evidence_path_present(evidence_root or Path("."), task.get("id", "?")) and not task.get("manual_override"):
            reasons.append("missing CLI transcript")
        review_report = str(task.get("review_report") or "")
        verdict = re.search(r"\b(PASS|PARTIAL|REWORK|BLOCKED)\b", review_report, re.I)
        if not verdict and not task.get("manual_override"):
            reasons.append("reviewer verdict missing")
        elif verdict and verdict.group(1).upper() != "PASS" and not task.get("manual_override"):
            reasons.append(f"reviewer verdict is {verdict.group(1).upper()}")
    if task.get("state") in ("BLOCKED", "FAILED"):
        if not task.get("reason"):
            reasons.append("blocked/failed requires reason")
    return reasons


def validate_dispatch_pack(task: dict) -> list[str]:
    errors = []
    required = ["id", "title", "project", "workspace", "detail", "verify_cmd", "assignee", "reviewer"]
    for key in required:
        if not task.get(key):
            errors.append(f"missing {key}")
    if not workspace_allowed(task.get("workspace", "")):
        errors.append("workspace outside allowlist")
    if is_doc_gate_cmd(str(task.get("verify_cmd", ""))):
        errors.append("verify_cmd is a task-package document grep gate")
    executor = task.get("executor") or {}
    if executor:
        for key in ("cli", "model", "command_template"):
            if not executor.get(key):
                errors.append(f"executor missing {key}")
        if executor.get("cli") not in ("claude", "codex", "opencode"):
            errors.append("executor.cli must be claude/codex/opencode")
    return errors


def normalize_completion_rows(rows: list[dict], pool_state_path: str | Path | None = None) -> list[dict]:
    state = {}
    if pool_state_path and Path(pool_state_path).exists():
        state = json.loads(Path(pool_state_path).read_text(encoding="utf-8"))
    normalized = []
    for row in rows:
        model = str(row.get("model", ""))
        provider = str(row.get("platform", ""))
        hits = MODEL_ALIAS_RE.findall(f"{provider} {model}")
        provider = hits[0].lower() if hits else provider
        row_state = ((state.get("providers") or {}).get(provider) or {}).get("status", "")
        out = dict(row)
        out["platform"] = provider
        out["pool_status"] = row_state
        out["cross_check_ok"] = bool(row_state in ("ok", "reachable") or not row_state)
        normalized.append(out)
    return normalized

# -*- coding: utf-8 -*-
"""R7: 历史任务迁移评审脚本（只读评审 + 分类写回 migrated 标签，不篡改 state/history）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("E:/Code/AideanCompany")
sys.path.insert(0, str(ROOT / "fleet" / "tools" / "verify"))
sys.path.insert(0, str(ROOT / "fleet" / "console"))

import gate_policy as g
from domain import done_gate_reasons

TASKS = ROOT / "fleet" / "console" / "state" / "tasks.json"
EVIDENCE = ROOT / "fleet" / "console" / "state" / "evidence"


def classify(task: dict) -> dict:
    reasons = done_gate_reasons(task)
    state = task.get("state")
    exec_exists = (EVIDENCE / f"{task.get('id')}-execution.json").exists()
    cli_exists = (EVIDENCE / f"{task.get('id')}-cli.log").exists()
    if state == "DONE":
        if not reasons:
            return {"class": "valid_legacy", "reasons": []}
        return {"class": "fake_done", "reasons": reasons}
    if state in ("BLOCKED", "FAILED") and not task.get("reason"):
        return {"class": "missing_reason", "reasons": ["blocked/failed requires reason"]}
    if not exec_exists and not cli_exists and state in ("SUBMITTED", "REVIEWING", "DOING"):
        return {"class": "missing_evidence", "reasons": ["in-flight but no runner evidence"]}
    return {"class": "needs_reverify", "reasons": reasons}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    apply_changes = "--apply" in argv
    data = json.loads(TASKS.read_text(encoding="utf-8"))
    out = []
    for t in data["tasks"]:
        c = classify(t)
        if apply_changes:
            t["migration_class"] = c["class"]
            t["migration_reasons"] = c["reasons"][:5]
        out.append({"id": t["id"], "state": t.get("state"), **c})
    if apply_changes:
        TASKS.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"apply": apply_changes, "tasks": out}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())


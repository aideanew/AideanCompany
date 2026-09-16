# -*- coding: utf-8 -*-
"""独立复查脚本：R8 复查骨架。只读，不改任务、不派工、不调 CLI。"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path("E:/Code/AideanCompany")
CONSOLE = ROOT / "fleet" / "console" / "console.py"
TASKS = ROOT / "fleet" / "console" / "state" / "tasks.json"
EVIDENCE = ROOT / "fleet" / "console" / "state" / "evidence"
AUDIT = ROOT / "fleet" / "console" / "state" / "audit.log"
MODEL_POOL = ROOT / "fleet" / "configs" / "model-pool.json"

CHECKS = []


def check(name, ok, detail=""):
    CHECKS.append({"name": name, "ok": bool(ok), "detail": detail})


def main():
    text = CONSOLE.read_text(encoding="utf-8", errors="replace")

    # 1. /close 是否仍有绕过门
    m = re.search(r"path\.startswith\(\"/tasks/\"\) and path\.endswith\(\"/close\"\).*?transition\(task, \"DONE\"",
                  text, re.S)
    check("close_has_gate", m is not None and "done_gate_reasons" in text[m.start():m.start()+2500])

    # 2. 派工是否经 Runner
    check("dispatch_calls_runner", "execute_task_pack(" in text and "cli_executed" in text)

    # 3. schema 拦截存在
    check("dispatch_schema_block", "dispatch_blocked_schema" in text)

    # 4. 旧 60/120 硬编码是否已移除
    check("no_legacy_60_120", "wait = 60 * tries" not in text)

    # 5. 假文档门识别
    sys.path.insert(0, str(ROOT / "fleet" / "tools" / "verify"))
    import gate_policy as g
    check("doc_gate_detected", g.is_doc_gate_cmd("grep:x/task-package-BE-01.md:kw"))

    # 6. 重试策略唯一来源
    check("retry_10x10", g.load_retry_policy(MODEL_POOL)["max_attempts"] == 10)

    # 7. tasks.json 假 DONE 扫描
    tasks = json.loads(TASKS.read_text(encoding="utf-8"))["tasks"]
    bad = []
    for t in tasks:
        if t.get("state") == "DONE":
            reasons = g.terminal_gate_reasons(t, evidence_root=str(EVIDENCE))
            manual = bool(t.get("manual_override"))
            if reasons and not manual:
                bad.append({"id": t["id"], "reasons": reasons[:3]})
    check("no_fake_done", not bad, json.dumps(bad, ensure_ascii=False)[:400])

    # 8. transcript 证据
    cli_logs = list(EVIDENCE.glob("*-cli.log"))
    check("cli_transcripts_present", len(cli_logs) > 0, f"count={len(cli_logs)}")

    # 9. 密钥扫描：设计文档与控制台内不应有明文 Key
    scan_targets = [ROOT / "初始设计" / "核心.md", CONSOLE, MODEL_POOL]
    leaks = []
    for p in scan_targets:
        if not p.exists():
            continue
        s = p.read_text(encoding="utf-8", errors="replace")
        for pat in (r"sk-[A-Za-z0-9]{16,}", r"nvapi-[A-Za-z0-9]{20,}", r"ms-[a-f0-9-]{20,}"):
            if re.search(pat, s):
                leaks.append(p.name)
    check("no_plaintext_keys", not leaks, ",".join(leaks))

    # 10. 审计事件链非空
    check("audit_exists", AUDIT.exists() and AUDIT.stat().st_size > 0)

    ok_all = all(c["ok"] for c in CHECKS)
    print(json.dumps({"pass": ok_all, "checks": CHECKS}, ensure_ascii=False, indent=2))
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())

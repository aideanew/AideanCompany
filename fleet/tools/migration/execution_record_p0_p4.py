# -*- coding: utf-8 -*-
"""P0-P4 execution record.

All times are local operator-machine times. No external CLI was launched.
"""
from __future__ import annotations


RECORD = {
    "P0": {
        "branch": "main",
        "base_commit": "78f56bc initial commit",
        "backups": "fleet/state/backups/P0-*",
        "freeze": "auto-dispatch OFF, auto-close OFF, all DONE require re-verify",
        "secrets": "secrets/KEY_INVENTORY.md created; core.md keys treated as leaked and pending rotation",
        "note": "console process check attempted via restart_console_v3.py --console-only (backgrounded, not relied upon)",
    },
    "P1": {
        "design_dirs": ["初始设计/00-索引", "01-需求", "02-架构", "03-协议", "04-运行手册", "05-安全", "06-决策记录", "07-验证计划", "99-归档"],
        "fleet_dirs": ["fleet/contracts", "fleet/runner", "fleet/dispatcher", "fleet/tools/*", "fleet/configs/*", "fleet/state/*", "fleet/console/*", "secrets"],
        "archive": "初始设计/99-归档/d0-d12 + MANIFEST.json",
        "policy": "d0-d12 archived read-only; 核心.md/异常.md/修复计划.md remain canonical until approved",
    },
    "P2P4": {
        "contracts": "fleet/contracts/contracts-v1.json (TaskPack/State/Event/Evidence/CompletionReport)",
        "runner": ["fleet/runner/cli_runner.py", "fleet/runner/retry_policy.py", "fleet/runner/command_registry.py"],
        "scheduler": "fleet/dispatcher/scheduler.py (DAG/lease/heartbeat/reclaim pure rules)",
        "smoke": "py_compile + import + contracts schema + build_cli_command dry-run PASS",
    },
}

# -*- coding: utf-8 -*-
"""CLI command registry.

Generated shape only; the real binary paths and --help output must be
calibrated on the operator machine during the verify stage. No CLI is
launched by importing this module.
"""
from __future__ import annotations

import json
from pathlib import Path


DEFAULT_REGISTRY = {
    "claude": {
        "binary": "claude",
        "mode": "non-interactive-print",
        "command_template": 'claude -p "@{PROMPT_FILE}" --output-format text --model {MODEL} --add-dir {WORKDIR}',
        "notes": "print mode skips interactive dialogs; --max-turns only valid in print mode",
    },
    "codex": {
        "binary": "codex",
        "mode": "exec",
        "command_template": 'codex exec --skip-git-repo-check -C {WORKDIR} -s workspace-write "{PROMPT_FILE}"',
        "notes": "requires explicit workdir; workspace-write is the file-write precondition",
    },
    "opencode": {
        "binary": "opencode",
        "mode": "run-once",
        "command_template": 'opencode run "@{PROMPT_FILE}" --dir {WORKDIR} -m {MODEL} --format json',
        "notes": "one-shot run does not need pty; do not share one workdir across parallel sessions",
    },
}


def write_default_registry(path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(DEFAULT_REGISTRY, ensure_ascii=False, indent=2), encoding="utf-8")
    return p

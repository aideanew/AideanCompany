# -*- coding: utf-8 -*-
"""secret_scan.py: scan repo for plaintext keys and emit machine-readable gate output.

Exit codes:
0 = clean
1 = findings
2 = scan error

Scope rules:
- Real secrets are allowed only in `secrets/.env`; that file is never scanned.
- `fleet/configs/skills-backup-*` trees are vendored third-party skill copies:
  they are reported as findings but flagged with `vendored=True`; scrub or move
  them into a quarantined archive, never edit individual upstream copies one by one.
- Placeholder shapes (sk-xxxx, YOUR_KEY, example...) are reported as info only.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path("E:/Code/AideanCompany")
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", "site-packages"}
SKIP_REL_PREFIXES = ("初始设计/99-归档",)
SKIP_FILE_NAMES = {".env", "secret_scan.py"}
VENDOR_DIR_MARKER = "skills-backup-"
MAX_FILE_BYTES = 2_000_000
SECRET_PATTERNS = [
    ("openai-like", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("nvidia", re.compile(r"\bnvapi-[A-Za-z0-9_-]{20,}\b")),
    ("modelscope", re.compile(r"\bms-[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b", re.I)),
    ("rc-key", re.compile(r"\brc-[a-f0-9]{40,}\b", re.I)),
    ("bearer-token", re.compile(r"Bearer\s+(?!\$\{)[A-Za-z0-9._~+/-]{24,}=*")),
    ("api-key-assignment", re.compile(
        r"(?i)\b(?:api[_-]?key|secret|access[_-]?token)\b\s*[:=]\s*[\"'](?!\$\{)(?!(?:sk-xxxx|YOUR_|your_))[A-Za-z0-9_\-./+=]{20,}[\"']")),
]
PLACEHOLDER_RE = re.compile(
    r"(?i)(xxxx|your[_-]?key|example|placeholder|changeme|redacted|\*{3,}|do_not|do-not|task-[a-f0-9]{16})")


def rel_posix(p: Path) -> str:
    return str(p.relative_to(ROOT)).replace("\\", "/")


def is_skipped(p: Path) -> bool:
    rp = rel_posix(p)
    if any(part in SKIP_DIRS for part in p.parts):
        return True
    if any(rp.startswith(x) for x in SKIP_REL_PREFIXES):
        return True
    if p.name in SKIP_FILE_NAMES or p.suffix.lower() == ".pyc":
        return True
    return False


def is_placeholder(value: str) -> bool:
    return bool(PLACEHOLDER_RE.search(value))


def scan_text(text: str) -> list[dict]:
    hits = []
    for name, rx in SECRET_PATTERNS:
        for m in rx.finditer(text):
            hits.append({"kind": name, "value": m.group(0),
                         "line": text[:m.start()].count("\n") + 1})
    return hits


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    include_vendored = "--include-vendored" in argv
    findings = []
    info = []
    for p in ROOT.rglob("*"):
        if not p.is_file() or is_skipped(p):
            continue
        try:
            if p.stat().st_size > MAX_FILE_BYTES:
                continue
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"scan_error={p}:{e}", file=sys.stderr)
            return 2
        vendored = VENDOR_DIR_MARKER in rel_posix(p)
        if vendored and not include_vendored:
            findings.append({"path": rel_posix(p.parent), "kind": "vendored-tree-skipped",
                             "line": 0, "sample": "move to quarantine", "vendored": True})
            continue
        for hit in scan_text(text):
            rec = {"path": rel_posix(p), "kind": hit["kind"], "line": hit["line"],
                   "sample": hit["value"][:8] + "***", "vendored": vendored}
            (info if is_placeholder(hit["value"]) else findings).append(rec)
    real = [r for r in findings if not r.get("vendored") or include_vendored]
    if as_json:
        print(json.dumps({"ok": not real, "findings": findings,
                          "info_placeholders": info}, ensure_ascii=False, indent=2))
    else:
        print(f"findings={len(real)} all={len(findings)} placeholders={len(info)}")
        for r in real:
            print(f"FINDING {r['path']}:{r['line']}:{r['kind']}:{r['sample']}")
    return 1 if real else 0


if __name__ == "__main__":
    sys.exit(main())

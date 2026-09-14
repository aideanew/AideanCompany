# Windows Environment (No WSL)

Session: 2026-05-28, AideanSynapse project scaffolding

## Environment Facts
- Host: Windows 11
- WSL bash: NOT available (`execvpe(/bin/bash) failed: No such file or directory`)
- `terminal` tool: broken (relies on WSL bash)
- `write_file` tool: broken (relies on WSL bash internally)
- Node.js: v24.12.0 at `C:\Program Files\nodejs\`
- npm: 11.7.0
- Docker: 29.4.3 (available, working)
- Python: 3.13 (execute_code works)

## What Works
- `execute_code` (Python) — use `subprocess.run(cmd, shell=True)` for any shell command
- `shell=True` is required for Windows to resolve PATH (npm, pnpm, node, docker)
- Python `open()` + `write()` for file creation
- `urllib.request` for HTTP health checks
- `socket` module for TCP port checks
- `pg8000` for PostgreSQL connections (pure Python, no C deps)

## What Doesn't Work
- `terminal` tool — requires WSL bash
- `write_file` tool — requires WSL bash
- Any POSIX shell syntax (no `ls`, `grep`, `cat`, `sed`)
- `pnpm approve-builds` interactive mode — use `shell=True` subprocess instead

## Docker Compose on Windows
- Docker Desktop works, but paths need forward slashes in compose files
- Volume mounts from Windows: use relative paths from project root
- Node dev containers work for frontend hot-reload when native Node isn't available

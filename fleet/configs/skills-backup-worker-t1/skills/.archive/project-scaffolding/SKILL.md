---
name: project-scaffolding
description: Scaffold complete full-stack projects from planning documents. Batch-create files, set up backend/frontend/infrastructure structure.
category: software-development
---

# Project Scaffolding

When the user provides planning documents and wants to scaffold a complete project from scratch.

## Trigger Conditions
- User provides planning/design documents and asks to build a project
- User wants to scaffold a full-stack application
- User says "build from scratch" or "scaffold the project"
- User provides a directory structure plan and wants all files created

## Steps

1. **Read all planning documents** - Load `.docs/` directory, requirements, architecture decisions
2. **Create directory structure** - Use `execute_code` with Python to batch-create directories
3. **Batch-create files** - Group files by module (10-15 per batch), use `execute_code` with Python
4. **Handle environment limitations** - If `write_file` fails (WSL missing), use `execute_code` with Python
5. **Verify** - List all created files, confirm structure matches plan

## File Creation Technique

See `references/batch-file-creation-technique.md` for detailed implementation.
See `references/windows-no-wsl-environment.md` for Windows-specific environment notes.
See `references/browser-testing-workflow.md` for serving production builds and browser verification.

When `write_file` is unavailable (WSL bash missing on Windows), use `execute_code` with Python:

```python
import os

project_dir = r"E:\path\to\project"

def write(rel_path, content):
    path = os.path.join(project_dir, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(content)
    print(f"  OK {rel_path}")

write("path/to/file.go", 'package main\nfunc main() {}')
```

## Go Project Structure Convention

```
backend/
├── cmd/server/main.go      # Entry point
├── config/                 # Configuration (config.yaml + loader)
├── internal/
│   ├── <module>/           # One module per business domain
│   │   ├── handler.go      # HTTP handlers (Gin)
│   │   ├── service.go      # Business logic
│   │   ├── repo.go         # Data access (pgx/ent)
│   │   ├── dto.go          # Request/Response DTOs
│   │   └── errors.go       # Domain-specific errors
│   ├── router/             # Route registration
│   └── middleware/          # Middleware (CORS, auth, recovery)
├── pkg/                    # Shared utilities
│   ├── response/           # Unified API response
│   ├── jwt/                # JWT token management
│   ├── ratelimit/          # Rate limiting
│   ├── httpclient/         # HTTP client pool
│   └── validator/          # Request validation
```

Each module follows: **Handler → Service → Repository** pattern with DTOs and errors.
- Handler: binds request, calls service, returns response
- Service: business logic, validation, transaction management
- Repository: SQL queries, data access, pagination

## Vite Monorepo Structure

```
frontend/
├── pnpm-workspace.yaml     # Workspace config
├── turbo.json              # Turborepo config
├── apps/
│   ├── admin/              # Admin panel (dark theme)
│   ├── console/            # User console (light theme)
│   └── public/             # Public marketing site
├── packages/
│   ├── ui/                 # Shared UI components
│   ├── utils/              # Shared utilities (API client, schemas)
│   ├── hooks/              # Shared React hooks
│   └── design-tokens/      # Design system tokens
```

Each app gets: `package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`, `src/main.tsx`, `src/App.tsx`, `src/globals.css`.

## Docker Compose Pattern

- **Dev compose**: separate services for DB, Redis, backend, each frontend app with hot-reload
- **Prod compose**: multi-stage builds, health checks, no exposed dev ports
- Use environment variables for all configuration
- Health checks on all services (postgres: `pg_isready`, redis: `redis-cli ping`, backend: `/health`)
- Volume mounts for persistent data

## Database Migration Pattern

- Numbered SQL files: `001_create_users.sql`, `002_create_channels.sql`, etc.
- Each migration: CREATE TABLE + indexes
- Seed files in `database/seeds/` for initial data
- Use `IF NOT EXISTS` for idempotency

## Auditing Existing Partial Projects

When a project already has partial scaffolding (some directories/files exist but many are missing or stubbed), do NOT scaffold from scratch. Instead:

1. **Read the planning document** — load the final directory structure plan (e.g., `.docs/执行规划/目录结构/最终方案.md`)
2. **Audit actual state** — navigate each directory level and check file sizes. Files <1KB are likely stubs; empty directories mean missing content. Use `browser_navigate` with `file://` URLs if filesystem tools are broken (see Pitfall #14).
3. **Classify each module** into three categories:
   - **✅ Complete**: Has real content (>2KB), working imports, non-trivial logic
   - - **⚠️ Stub**: Directory exists with skeleton files (handlers return 501, repos return "not implemented")
   - **❌ Missing**: Directory or key files do not exist at all
4. **Generate gap analysis** — list all ❌ items with the exact files needed, grouped by module
5. **Output creation scripts** — generate PowerShell/Shell scripts organized by module, so the user can execute them locally

See `references/gap-analysis-audit-workflow.md` for the detailed audit checklist and reporting format.

## Pitfalls

1. **Go comments in Python strings**: When embedding Go code in Python triple-quoted strings, `//` comments can cause syntax errors if they appear at the start of a line in certain contexts. Use single-quoted strings or split into separate write calls.
2. **Batch size**: Keep file creation batches to 10-15 files to avoid timeout. Split large modules across multiple `execute_code` calls.
3. **Directory creation**: Always create directories before files. Use `os.makedirs(exist_ok=True)`.
4. **UTF-8 encoding**: Always specify `encoding='utf-8'` when opening files in Python.
5. **Line endings**: Use `newline='\n'` for consistent Unix line endings on Windows.
6. **Import paths**: Use the correct Go module path from `go.mod` in all imports.
7. **Placeholder handlers**: Create route registrations with placeholder handlers that return 501, so the router compiles immediately.
8. **pnpm peer dependency warnings**: pnpm may report peer dependency issues or ignore build scripts (esbuild). These are non-blocking — Vite resolves esbuild via npx at runtime. Do not block on these warnings.
9. **Existing services on ports**: Before starting new services, check if ports are already in use (previous sessions may have left services running). Use `socket.connect_ex()` to probe before attempting to start. Kill old node processes: `Stop-Process -Id <pid> -Force` via PowerShell.
10. **pnpm dev fails with deps status check**: `pnpm dev --filter @aidean/admin` may exit with code 1 due to `runDepsStatusCheck` failure. Use `npm run dev` from the app directory instead — it bypasses the pnpm workspace status check.
11. **Vite HMR WebSocket breaks remote browser testing**: When the browser tool connects to a Vite dev server, HMR WebSocket fails (remote browser can't reach localhost WS). React renders blank. **Solution**: build production (`npm run build`) and serve `dist/` for browser testing.
12. **Serving production builds on Windows**: `python -m http.server` may close connections without response. Use a Node.js static server with PowerShell `Start-Process -WorkingDirectory` (see `references/browser-testing-workflow.md`).
13. **WSL relay total failure**: If `terminal`, `write_file`, AND `execute_code` ALL fail with `CreateProcessCommon:800: execvpe(/bin/bash) failed`, the WSL bash relay is completely broken. Do NOT retry any of these tools — they will all fail. Instead: (a) use `browser_navigate` with `file://` URLs to audit existing files, (b) output complete PowerShell/Shell scripts in the response for the user to execute locally. See `references/windows-no-wsl-environment.md` for diagnostics.
14. **Auditing partial projects**: When a project has existing scaffolding, do NOT re-scaffold from scratch. Audit actual state first (see "Auditing Existing Partial Projects" section above). Classify modules as Complete/Stub/Missing and only generate scripts for the gaps.

## Frontend Dependency Installation (Windows)

On Windows without WSL, `terminal` tool and `write_file` are unavailable. Use `execute_code` with Python subprocess and `shell=True`:

```python
import subprocess

frontend_dir = r"E:\path\to\frontend"

# Install pnpm globally (if not present)
subprocess.run(["npm", "install", "-g", "pnpm"], shell=True, capture_output=True)

# Install workspace dependencies
subprocess.run(["pnpm", "install"], shell=True, cwd=frontend_dir, capture_output=True, timeout=300)
```

Key: always use `shell=True` so Windows finds npm/pnpm in PATH. pnpm may warn about peer dependencies or ignored build scripts (esbuild) — these are non-blocking; Vite will use npx to resolve esbuild at runtime.

## Browser Testing Workflow

When the browser tool is available, verify frontend builds independently:

1. **Build all apps**: `npm run build` in each app directory
2. **Serve production builds**: Use Node.js static server (see `references/browser-testing-workflow.md`) — Python http.server is unreliable on Windows
3. **Test each app in browser**: Navigate to each port, verify rendering, check console for JS errors
4. **Test routing**: Click navigation links, verify page transitions work
5. **Screenshot verification**: Use `browser_vision` to confirm visual rendering

Do NOT test Vite dev servers via browser tool — HMR WebSocket fails for remote browsers, causing blank pages.

## Service Verification

After scaffolding, verify all services are running:

```python
import urllib.request, json, socket

# Check HTTP services
for name, url in [("Backend", "http://localhost:10010/health"), ("Admin", "http://localhost:5173")]:
    try:
        resp = urllib.request.urlopen(url, timeout=3)
        print(f"OK {name}: HTTP {resp.status}")
    except Exception as e:
        print(f"FAIL {name}: {e}")

# Check TCP ports (database, redis)
for name, port in [("PostgreSQL", 5432), ("Redis", 6379)]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(f"{'OK' if s.connect_ex(('localhost', port)) == 0 else 'FAIL'} {name}:{port}")
    s.close()
```

## Verification

After scaffolding:
1. List all files created with counts per directory
2. Confirm directory structure matches the plan
3. Verify each module has handler/service/repo/dto/errors
4. Check that imports and module references are consistent
5. Confirm Docker compose files reference correct paths and ports
6. Hit health endpoints and verify database/redis connectivity (see Service Verification above)

---
name: read-only-codebase-verification
description: "Verify planned code changes against actual codebase when file tools are blocked (e.g. broken WSL). Uses execute_code with Python as primary method, browser-based file reading as fallback. Triggers on: read-only verification, check task completion, verify code changes, WSL broken, file tools unavailable."
version: 2.0.0
author: Hermes Agent
license: MIT
platforms: [windows, linux, macos]
---

# Read-Only Codebase Verification

Verify planned code changes against actual codebase content when standard file tools (write_file, patch, terminal) are unavailable or blocked. Also used for auditing multi-phase task completion against planned work.

## When to Use

- User asks to verify/check task completion against actual code (read-only, no edits)
- WSL is broken on Windows (`CreateProcessCommon:800: execvpe(/bin/bash) failed`)
- File writing tools fail but reading is still needed
- Environment constraints prevent terminal access
- User explicitly says "禁止编辑和新建文件" (prohibit editing/creating files)
- User asks to audit planned tasks against actual implementation
- Chinese triggers: "审查", "检查任务完成情况", "读取最新文件", "代码文件已全量更新", "带编号分论点输出"

See also: `references/project-task-verification-pattern.md` for the common `.docs/Parses/` project structure.

## execute_code with Python (Primary Recommended Method)

`execute_code` works reliably even when `terminal` is broken. Use Python's `os`, `re`, and `json` modules for comprehensive file system inspection:

```python
import os, re

project_dir = r"E:\path\to\project"

# List directory contents with sizes
for item in os.listdir(os.path.join(project_dir, ".docs")):
    path = os.path.join(project_dir, ".docs", item)
    if os.path.isfile(path):
        print(f"{item} ({os.path.getsize(path)} bytes)")
    else:
        print(f"{item}/ (directory)")

# Read file content (chunk large files)
with open(os.path.join(project_dir, "file.md"), 'r', encoding='utf-8') as f:
    content = f.read()
    print(content[:5000] if len(content) > 5000 else content)

# Search for keywords across all files in a directory tree
for root, dirs, files in os.walk(project_dir):
    if 'node_modules' in root or '__pycache__' in root:
        continue
    for file in files:
        if file.endswith(('.py', '.tsx', '.ts')):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'keyword' in content:
                        rel_path = os.path.relpath(filepath, project_dir)
                        print(f"Found in {rel_path} ({content.count('keyword')} occurrences)")
            except:
                pass

# Check multiple files existence and size
for filepath in ["path/to/file1.py", "path/to/file2.tsx"]:
    full = os.path.join(project_dir, filepath)
    exists = os.path.exists(full)
    size = os.path.getsize(full) if exists else 0
    print(f"{'✅' if exists else '❌'} {filepath} ({size} bytes)")

# Regex search within a file
with open(os.path.join(project_dir, "api/db/models.py"), 'r', encoding='utf-8') as f:
    content = f.read()
# Find class definition and its fields
match = re.search(r'class Tenant.*?(?=class |\Z)', content, re.DOTALL)
if match:
    print("Found Tenant class")
    # Check for specific fields
    for field in ['login_policy', 'team_mode', 'ocr_id']:
        print(f"  {'✅' if field in match.group() else '❌'} {field}")
```

**Advantages**: No path encoding issues, handles Chinese characters in filenames, processes multiple files per call, supports regex search, no browser session overhead. Works even when WSL/terminal is broken.

## Browser-Based File Reading (Secondary Fallback)

When BOTH `terminal` AND `execute_code` fail:

### Step 1: Navigate to file via browser

```
browser_navigate(url="file:///E:/path/to/file.md")
```

### Step 2: Extract text content via browser_console

```
browser_console(expression="document.querySelector('pre').textContent.substring(0, 8000)")
```

This works because browsers render `.md`, `.py`, `.ts`, `.json`, and other text files as `<pre>` blocks when opened via `file:///` URLs.

### Step 3: For larger files, paginate

```javascript
document.querySelector('pre').textContent.substring(0, 8000)
document.querySelector('pre').textContent.substring(8000, 16000)
```

### Step 4: List directories

```
browser_navigate(url="file:///E:/path/to/directory/")
```

## Multi-Phase Task Verification Workflow

When verifying planned tasks (e.g., from `.docs/Parses/`) against actual code:

1. **Read planning documents** — load `temp.md` (master task list), `readme.md` (requirements), and each Phase document in `Parses/`
2. **Identify target files** — from each Phase document, determine which source files should have been modified
3. **Verify file existence** — check that new files were created and modified files exist
4. **Verify implementation** — search for key functions, classes, keywords, i18n keys in actual source code
5. **Check both backend and frontend** — many tasks require changes in both `api/` and `web/src/`
6. **Cross-reference** — verify temp.md task descriptions match actual code evidence
7. **Identify gaps** — note missing implementations, technical debt, incomplete tasks
8. **Report** — output numbered conclusions with credible evidence, confidence levels, completion percentages

## Full-Stack Requirement-by-Requirement Verification

When the user says "检查所有需求，依次阅读 readme.md 每个要点" (check all requirements, read each readme.md point in order), perform a deep full-stack audit per requirement:

1. **Read readme.md** — parse each requirement point (user may use "-----" as separator)
2. **For EACH requirement, verify ALL layers**:
   - **数据库 (Database)**: check `db_models.py` for relevant model classes, fields, migrations
   - **后端API (Backend API)**: check `api/apps/` for route handlers, request/response logic
   - **后端服务 (Backend Services)**: check `api/db/services/` and `api/utils/` for business logic
   - **前端页面 (Frontend Pages)**: check `web/src/pages/` for UI components
   - **前端服务 (Frontend Services)**: check `web/src/services/` for API call definitions and TypeScript types
   - **i18n国际化**: check `web/src/locales/` — ALL 13 language files must have the relevant keys
   - **关联性 (Cross-module)**: check if the feature connects to related modules (e.g., Skills → Agent Canvas → Admin)
   - **增删改查 (CRUD)**: verify Create, Read, Update, Delete operations are all implemented
3. **Report per requirement**: use "-----" as separator between requirements, state ✅/❌/⚠️ with layer-by-layer evidence table
4. **Never skip layers** — a feature with backend but no frontend API endpoint is incomplete; a frontend component with no backend model is a stub

This workflow was established by the user's explicit instruction: "基于实际代码结构，分析是否完成该功能，数据库、API、前后端、油猴脚本、关联性、增删改查等是否都全部实现" — every requirement must be checked across ALL these dimensions, not just a surface-level keyword search.

## Cross-Session Verification Discipline

When user says "代码文件已全量更新" (code files fully updated) or "重新审查" (re-verify):
- **NEVER trust previous session conclusions** — files may have been modified, reverted, or newly created
- Re-verify EVERY item from scratch, including items previously marked ✅
- Previous session's context compaction summary is a starting point, not ground truth
- A previously "fixed" item may have been reverted; a previously "broken" item may now be fixed
- Report status changes vs. previous verification (e.g., "上次✅本次❌" = regressed)

## Audit Report Cross-Validation Workflow

When user provides a previous audit/verification report (材料一, 材料二, etc.) and asks you to cross-validate against actual code:

1. **Extract every claim** from the report into a verification checklist (numbered, one claim per item)
2. **Re-verify each claim independently** against actual code — do NOT accept or reject based on report authority
3. **Track file sizes** at each verification round — if sizes are identical across rounds, code has not changed and previous conclusions stand
4. **Report three categories**: (a) claims confirmed correct, (b) claims proven WRONG with code evidence, (c) claims omitted/overlooked by the report
5. **Highlight report errors prominently** — e.g., "终审报告错误：将 3.1.1 误判为 P0，代码明确显示已完整实现"
6. **Correct the priority distribution** — a report may claim P0 issues that are actually P1, or miss P1 issues entirely

**File size comparison technique** (detects if code actually changed between verification rounds):
```python
known_sizes = {"path/to/file.tsx": 7411, "path/to/other.py": 2985}
for fp, prev_size in known_sizes.items():
    full = os.path.join(project_dir, fp)
    if os.path.exists(full):
        curr = os.path.getsize(full)
        changed = "CHANGED" if curr != prev_size else "UNCHANGED"
        print(f"  {changed}: {fp}: {prev_size} → {curr}")
```
If ALL files are UNCHANGED, you can confidently carry forward previous conclusions without re-parsing every file.

## i18n Coverage Verification

When verifying internationalization completeness, check ALL locale files (typically 13 languages):
```python
locales_dir = os.path.join(project_dir, "web/src/locales")
locale_files = [f for f in os.listdir(locales_dir) if f.endswith('.ts') and f not in ['config.ts', 'until.ts']]
for key in ['copyShareLink', 'versionMode']:
    covered = sum(1 for lf in locale_files if key in open(os.path.join(locales_dir, lf), 'r', encoding='utf-8').read())
    print(f"  {key}: {covered}/{len(locale_files)}")
```
Report as `covered/total` (e.g. "2/13"). Keys with 0/13 or <13/13 are incomplete i18n gaps.

1. **Read-only only** — cannot write, edit, or create files
2. **Binary files won't render** in browser — only text-based files (`.md`, `.py`, `.ts`, `.tsx`, `.json`, `.yaml`, `.html`, `.css`, etc.)
3. **Large files need chunking** — read in segments for files >5000 chars
4. **Path format matters** — use `file:///E:/path` on Windows, not `file:///e/path`
5. **Keyword search is surface-level** — finding a keyword in a FILE doesn't prove the SPECIFIC FUNCTION uses it. A keyword may appear in a different function, a comment, or an import. Always extract the full function body (from `def` to next `def`/blank-line boundary) and verify the logic is inside that function.
6. **Wrapper-forwarding trap** — a function like `get_tokens_used_monthly()` may simply `return get_tokens_used(tenant_id)` with no actual monthly filtering. The "monthly" keyword exists in the function NAME but the implementation is a no-op forward. Always check the callee too.

## Function Body Extraction (Critical for Accurate Verification)

When verifying a specific function's implementation, NEVER rely on file-level keyword grep. Extract the full function body:

```python
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
# Find function start
for i, line in enumerate(lines):
    if 'def target_function(' in line:
        start = i
        # Extract until next def or end-of-indent
        for j in range(i+1, len(lines)):
            if lines[j] and not lines[j].startswith(' ') and not lines[j].startswith('\t'):
                func_body = '\n'.join(lines[start:j])
                break
        else:
            func_body = '\n'.join(lines[start:])
        # NOW check for the specific logic
        has_filter = any(kw in func_body for kw in ['month_start', 'created_at', 'datetime.now'])
```

This prevents the "keyword in wrong function" false positive (e.g., `month` keyword found in `check_token_quota` but the function being verified is `get_tokens_used_monthly` which just forwards to `get_tokens_used`).

## Output Format (User Preference)

- Numbered points (带编号分论点) with credible conclusions
- **STRICTLY NO CODE in output** — analysis only. User explicitly says "禁止输出大量代码" (prohibit outputting large amounts of code), repeated **3× for maximum emphasis**. Report file paths, line numbers, and logic descriptions — never paste code blocks. The user may triple-reiterate this rule ("禁止输出大量代码。禁止输出大量代码。禁止输出大量代码.) — treat this as a hard constraint, not a suggestion.
- State confidence level per finding (置信度)
- Report completion percentage (完成度) — use **layered partial-completion scoring** (see below)
- Highlight missing items with connection to temp.md and readme.md
- Summary table with overall confidence and completion
- When cross-validating a previous report: include a dedicated section mapping each report claim to code fact (终审报告交叉验证结论), explicitly labeling "终审正确" / "终审错误" / "终审遗漏"

### Layered Partial-Completion Scoring

When a task spans multiple layers (backend logic, API endpoint, frontend UI, etc.), report completion as a weighted sum of layer statuses rather than binary pass/fail:

```
完成度: 33% (后端逻辑 100% + API端点 0% + 前端UI 0%)
完成度: 40% (后端 100% + 配置页 100% + 前端TagType 0%)
完成度: 25% (4个长列表页面中仅1个完成)
```

This gives the user precise signal about WHERE the gap is, not just that a gap exists. Always break down by the natural layers of the feature (backend logic → API endpoint → frontend service type → frontend UI component).

### Multi-Round Verification Comparison

When the user says "代码文件已全量更新，重新审查" (code fully updated, re-verify), produce a **comparison table** showing status changes between rounds:

```
| 维度 | 上轮 | 本轮 | 变化 |
|------|------|------|------|
| 总待修复项 | 9 项 | 4 项 | -5 项 ✅ |
| P1 未完成 | 7 项 | 4 项 | -3 项 ✅ |
| 整体完成度 | 94.7% | 97.3% | +2.6% ✅ |
```

This lets the user immediately see what was fixed and what remains. File size comparison (see above) is the primary mechanism for detecting which items actually changed vs. which are carryovers.

## Common Error Patterns

| Error | Cause | Fix |
|-------|-------|-----|
| `WSL CreateProcessCommon:800: execvpe(/bin/bash) failed` | WSL not installed or broken | Use `execute_code` with Python, or browser-based reading |
| `File not found` from read_file | Path resolution issue with WSL backend | Use `execute_code` with Python `os.path.join()` |
| `File search requires 'rg' (ripgrep) or 'find'` | ripgrep not installed | Use `execute_code` with Python `os.walk()` |
| Empty response from browser | Binary file or non-text content | Skip binary files, use only for text |

## Schema-Constraint Blocking (Pitfall)

When a task requires time-based filtering (e.g., "monthly token usage"), the implementation may be blocked by database schema — the relevant model may lack a `created_at` / `create_time` timestamp field. In this case:

1. **Verify the model schema first** — check db_models.py for the target model's fields
2. **If no timestamp exists**, the task cannot use simple WHERE-time filtering
3. **Report the blocking constraint explicitly** — e.g., "TenantLLM 无 create_time 字段，无法实现月度统计"
4. **Offer alternative approaches**: (a) rename field to match actual semantics (e.g., `max_tokens_monthly` → `max_tokens_lifetime`), (b) create a new tracking table with timestamps, (c) frontend-only workaround (rename the label)
5. **Do NOT claim the task is "incomplete" without explaining WHY** — the root cause is a schema gap, not a missing implementation

This pattern emerged from the RagFlow Token monthly semantics issue: `get_tokens_used_monthly()` appeared to be a no-op (just forwarding to `get_tokens_used`), but the real blocker was that `TenantLLM` model has no `create_time` field, making time-filtered queries impossible without schema migration.

## Tool Reliability Hierarchy (When WSL is Broken)

| Tool | Works when WSL broken? |
|------|----------------------|
| `execute_code` (Python) | ✅ YES — uses Python directly |
| `browser_*` tools | ✅ YES — independent of WSL |
| `memory` / `skill_*` tools | ✅ YES — independent of WSL |
| `terminal` | ❌ NO — requires bash |
| `write_file` / `patch` | ❌ NO — uses WSL backend |
| `search_files` | ❌ NO — requires ripgrep via WSL |

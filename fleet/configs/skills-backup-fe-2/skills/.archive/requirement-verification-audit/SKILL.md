---
name: requirement-verification-audit
description: "Systematically verify codebase implementation against requirements documents (readme.md, temp.md, Parses/). Read-only audit checking database, API, frontend, backend, i18n, CRUD completeness. Triggers on: 检查所有需求, 审查代码, 验证完成度, 逐项检查, 代码文件已全量更新, 重新审查, requirement verification, codebase audit, 禁止编辑和新建文件."
version: 1.0.0
author: Hermes Agent
---

# Requirement Verification Audit

Systematically verify whether a codebase fully implements requirements from planning documents. Read-only — never edit or create files.

## When to Use

- User says "检查所有需求" (check all requirements) or "逐个检查" (check each one)
- User says "代码文件已全量更新，重新审查" (code fully updated, re-verify)
- User says "禁止编辑和新建文件" (prohibit editing/creating files) for verification tasks
- User wants to verify temp.md / readme.md / Parses/ task completion against actual code
- User asks for completion percentage and confidence level of implemented features
- User says "基于实际代码结构，分析是否完成该功能" — full-stack audit per requirement

## File Discovery (First Step When Structure Is Unknown)

Before reading requirements documents, discover the actual project structure when standard paths fail (read_file returns "File not found", terminal is broken):

```python
import os

project_root = r"E:\path\to\project"

# Walk entire tree to find all files with sizes
for root, dirs, files in os.walk(project_root):
    # Skip common non-source directories
    dirs[:] = [d for d in dirs if d not in ('.git', 'venv', '__pycache__', 'node_modules')]
    for f in files:
        fp = os.path.join(root, f)
        rel = os.path.relpath(fp, project_root)
        size = os.path.getsize(fp)
        print(f"{rel} ({size} bytes)")

# Read a file once structure is known
with open(os.path.join(project_root, "readme.md"), 'r', encoding='utf-8') as f:
    print(f.read())
```

This avoids the `read_file` tool's path resolution issues (backslash vs forward slash on Windows) and `search_files`' ripgrep dependency. Use `execute_code` with Python as the primary file access method when terminal is broken.

## Core Principle

Every requirement must be verified across ALL layers relevant to THIS PROJECT, not just surface-level keyword search. The natural layers depend on the project's architecture:

- **Monorepo with separate frontend/backend** (e.g., api/ + web/src/): verify db_models, API routes, services, frontend pages, frontend services, i18n
- **Single-server web app** (e.g., server/ with templates/): verify database models, API routers, service modules, HTML templates, JS/CSS frontend files
- **Browser-script projects** (e.g., tampermonkey/): verify script selectors, data collection, navigation logic, error handling, server-side reception API
- **Always check**: 数据库 (Database models), 后端 (Backend API/routes), 前端 (Frontend UI), 关联性 (Cross-module connections), 增删改查 (CRUD completeness)

## Core Principle

Every requirement must be verified across ALL layers relevant to THIS PROJECT, not just surface-level keyword search. The natural layers depend on the project's architecture:

- **Monorepo with separate frontend/backend** (e.g., api/ + web/src/): verify db_models, API routes, services, frontend pages, frontend services, i18n
- **Single-server web app** (e.g., server/ with templates/): verify database models, API routers, service modules, HTML templates, JS/CSS frontend files
- **Browser-script projects** (e.g., tampermonkey/): verify script selectors, data collection, navigation logic, error handling, server-side reception API
- **Always check**: 数据库 (Database models), 后端 (Backend API/routes), 前端 (Frontend UI), 关联性 (Cross-module connections), 增删改查 (CRUD completeness)

A feature with backend but no frontend API endpoint is incomplete. A frontend component with no backend model is a stub. A browser script without corresponding server-side reception is incomplete.

## Verification Workflow

### Step 1: Read Requirements Documents
- Read `.docs/readme.md` — primary requirements document
- Read `.docs/temp.md` — master task list with phases
- Read `.docs/Parses/` — individual task phase documents
- Parse each requirement into a verification checklist

### Step 2: Verify Each Requirement
For each requirement, use `execute_code` with Python to:

**Layer 1 — Existence check** (file exists, model defined, route registered):
```python
import os, re

project_dir = r"project_root"

# Check file existence and size
p = os.path.join(project_dir, "path/to/file.tsx")
exists = os.path.exists(p)
size = os.path.getsize(p) if exists else 0

# Read and search file content
with open(p, 'r', encoding='utf-8') as f:
    content = f.read()
    has_keyword = 'keyword' in content

# Search across directory tree
for root, dirs, files in os.walk(target_dir):
    for file in files:
        if file.endswith('.tsx'):
            fp = os.path.join(root, file)
            with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                if 'keyword' in f.read():
                    print(f"Found in {os.path.relpath(fp, project_dir)}")
```

**Layer 2 — Logic depth check** (function body extraction, not just keyword presence):
When a keyword match is found, extract the surrounding function/method body to verify the feature is actually implemented, not just named:
```python
# Extract function body to verify actual logic
content = open(filepath).read()
idx = content.find('functionName')
# Find the function definition
fn_start = content.rfind('def functionName', 0, idx+50)
# Extract ~500 chars of function body
function_body = content[fn_start:fn_start+800]
print(function_body)
# NOW judge: does this function actually do what the requirement asks?
```

**Layer 3 — Cross-layer connectivity check**:
```python
# Check that frontend template links to backend API
template_content = open(template_path).read()
api_content = open(api_path).read()
# Verify: does the template call the API endpoint?
endpoint_name = '/api/some-endpoint'
print(f"Frontend calls API: {endpoint_name in template_content}")
print(f"Backend serves API: {endpoint_name in api_content}")
# Verify: is the page reachable from navigation?
nav_content = open('base.html').read()
page_path = '/some-page'
print(f"Nav link exists: {page_path in nav_content}")
```

### Step 3: Score Each Requirement
Use layered partial-completion scoring:

- **✅ 已完成 (Complete)**: All layers implemented (100%)
- **⚠️ 基本完成 (Mostly Complete)**: Core layers done, minor gaps (70-90%)
- **❌ 未完成 (Incomplete)**: Missing critical layers (<70%)

Report partial completion by layer:
```
完成度: 33% (后端逻辑 100% + API端点 0% + 前端UI 0%)
完成度: 40% (后端 100% + 配置页 100% + 前端TagType 0%)
```

### Step 4: Output Format

Per requirement:
```
### [Requirement Number] Requirement Title
-----
**需求**: Original requirement text
**验证结果**: ✅/⚠️/❌ Status

| 层级 | 文件 | 状态 |
|------|------|------|
| 数据库 | db_models.py:line | ✅/❌ |
| 后端API | api/apps/file.py | ✅/❌ |
| 前端UI | web/src/pages/file.tsx | ✅/❌ |

**缺失项**: Specific gaps (if any)
**置信度**: XX%
```

### Step 5: Summary Table
```
| 维度 | 数值 |
|------|------|
| 总需求项 | N 项 |
| 完全完成 | X 项 (XX%) |
| 基本完成 | Y 项 (YY%) |
| 未完成 | Z 项 (ZZ%) |
| 整体完成度 | XX% |
| 整体置信度 | XX% |
```

### Step 5b: Module-Level Summary (When Requirements Are Grouped)

When the user's readme.md uses "-----" separators to divide requirements into modules (e.g., 基础系统, 排班功能, 投流规则), report completion PER MODULE:

```
## 总体汇总
| 需求模块 | 完成度 | 核心缺失 |
|----------|--------|----------|
| 一、基础系统 | **95%** | 无重大缺失 |
| 二、排班功能 | **80%** | 一键排班缺失 |
| 三、投流规则 | **40%** | 投流计划管理完全缺失 |
```

Then list **关键缺失按优先级排序** (key missing items ranked by priority).

## Requirement Document Patterns

- **readme.md with "-----" separators**: User may group requirements into modules separated by "-----" lines. Parse each module independently and report per-module completion.
- **Single-item requirements**: Each bullet/paragraph is a self-contained requirement to verify.
- **Parses/ directory**: Contains phase-by-phase execution plans. Cross-reference with actual code changes.

## Output Rules

1. **禁止输出代码** — report file paths, line numbers, logic descriptions. Never paste code blocks.
2. **带编号分论点** — numbered conclusions with credible evidence
3. **置信度** — confidence level per finding
4. **完成度** — completion percentage with layered breakdown
5. **突出缺失项** — explicitly connect missing items to temp.md and readme.md phases

## Common Pitfalls

- **Keyword in wrong function**: Finding "cache" in a file doesn't mean the specific function has cache logic. Extract full function body.
- **Wrapper-forwarding trap**: `get_tokens_used_monthly()` may just `return get_tokens_used()` — the "monthly" is in the name only.
- **Schema blocking**: A model may lack `created_at` field, making time-based filtering impossible without migration.
- **i18n partial coverage**: Keys may exist in en.ts and zh.ts but be missing from 11 other language files.
- **Stub implementations**: A file may exist but contain only placeholder comments or empty functions.
- **Browser script keyword false positive**: "account" in a Tampermonkey script's CONFIG doesn't mean account-level data differentiation is implemented. Check the actual data payload sent to the server.
- **Button-exists ≠ feature-complete**: A "一键排班" button may only fill anchor_mapping slots by rotating fulltime/parttime lists — not actually generate a full week's schedule. Extract the function body and trace its logic, don't stop at finding the button element.
- **Model-exists ≠ analysis-implemented**: An AdPlanSpend model with CRUD API doesn't mean "投流效果→下场策略分析" is implemented. Check for actual analysis/aggregation logic, not just data storage.
- **Requirement keyword ≠ code keyword**: A requirement for "总览" tab may be implemented under a different name. Check system Tab configurations and their actual content, not just string matches.
- **Field-exists-in-model ≠ field-displayed-in-UI**: `ClueAssignment.assigned_at` existing in the model doesn't mean "分配时间" is shown in the clue board table. Check the actual `<th>` column headers in the template.
- **Nav link gap**: A new page (e.g., anchor_stats.html) is invisible to users if `base.html` sidebar/nav doesn't link to it. Always check navigation registration for new pages.

See also: `references/browser-script-project-verification.md` for verifying projects with Tampermonkey/browser automation scripts.
See also: `references/live-broadcast-project-verification.md` for patterns discovered in live broadcast data analysis projects (FastAPI + Jinja2 + Tampermonkey architecture).

## Cross-Session Verification

When user says "代码文件已全量更新" (code fully updated):
- NEVER trust previous conclusions — re-verify everything from scratch
- Compare file sizes to detect what changed: if size is identical, code likely unchanged
- Report status changes vs. previous verification round

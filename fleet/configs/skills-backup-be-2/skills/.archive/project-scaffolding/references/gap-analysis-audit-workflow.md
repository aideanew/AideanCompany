# Gap Analysis & Audit Workflow

When a project already has partial scaffolding and you need to identify what's missing vs. the plan.

## Audit Procedure

### Step 1: Load the Plan
Read the final directory structure plan (e.g., `.docs/执行规划/目录结构/最终方案.md`).
Extract the complete expected directory tree.

### Step 2: Audit Actual State
Navigate each directory level using `browser_navigate` with `file://` URLs.
For each file, note:
- **File size**: <1KB = likely stub/placeholder; >2KB = likely has real content
- **File content**: Check if handlers return 501, repos return "not implemented", services are empty
- **Directory emptiness**: Empty directories mean missing content

### Step 3: Classify Modules

| Category | Symbol | Criteria |
|----------|--------|----------|
| Complete | ✅ | Real content (>2KB), working imports, non-trivial business logic |
| Stub | ⚠️ | Files exist but return "not implemented", handlers return 501, empty service methods |
| Missing | ❌ | Directory or key files do not exist at all |

### Step 4: Generate Gap Report

Format the gap report as:

```
## 当前项目实际完成状态审计

### ✅ 已完成（真实有效）
| 模块 | 完成度 | 说明 |
|------|--------|------|

### ⚠️ 仅有骨架（Stubs/占位符）
| 模块 | 现状 | 问题 |
|------|------|------|

### ❌ 完全缺失
| 模块 | 缺失内容 |
|------|----------|
```

### Step 5: Generate Creation Scripts

For each ❌ item, generate the exact files needed. Group by module.
Output as PowerShell scripts (Windows) or Shell scripts (Linux/Mac).

## Browser File Navigation Technique

When filesystem tools are broken, use:
```
browser_navigate(url="file:///E:/path/to/directory/")
```
This shows a directory listing. Click links to navigate into subdirectories.
Use `browser_console(expression="document.body.innerText")` to read file contents.

## Cross-Reference with Other Plans

After auditing directory structure, cross-reference with:
- API接口/最终方案.md — verify all route groups and endpoints are registered
- 技术架构/最终方案.md — verify tech stack matches (ORM, middleware, etc.)
- 数据库/最终方案.md — verify migration files match expected tables
- UI设计/最终方案.md — verify frontend pages match expected routes

## Milestone Mapping

Map gaps to execution milestones (M1-M10 from 执行规划/最终方案.md):
- M1: Infrastructure (Ent Schema, Docker, config)
- M2: Authentication (JWT, middleware, login/register)
- M3: Channel management
- M4: Gateway/Relay engine
- M5: Billing engine
- M6: Payment & marketing
- M7: Enterprise features
- M8: Frontend pages
- M9: Statistics & notifications
- M10: Deployment & integration

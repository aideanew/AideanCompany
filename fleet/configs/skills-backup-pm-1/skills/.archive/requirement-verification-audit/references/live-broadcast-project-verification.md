# Live Broadcast Project Verification Patterns

Discovered during AliveBroadcastData full-stack audit (2026-06-06).

## Project Architecture

Single-server web app (FastAPI + Jinja2 + SQLite + Tampermonkey):
- `server/models.py` — all database models (SQLAlchemy)
- `server/routers/admin.py` — admin API endpoints
- `server/routers/api.py` — public API endpoints
- `server/routers/pages.py` — page routes (HTML templates)
- `server/templates/` — frontend HTML templates
- `server/templates/admin/` — admin HTML templates
- `server/services/` — business logic modules
- `tampermonkey/` — browser automation scripts

## Verification Patterns

### Pattern 1: Requirement Keyword ≠ Code Keyword
A requirement for "总览" (overview) tab may be implemented under a different name. Don't just grep for the exact requirement text — check system configurations, default data, and actual rendered content.

### Pattern 2: Button Exists ≠ Feature Complete
"一键排班" (one-click scheduling) button was found in the template, but `autoFillAnchors()` only fills anchor_mapping slots by rotating fulltime/parttime lists — not generating a full week's schedule. Always extract and read the function body.

### Pattern 3: Model Exists ≠ Analysis Implemented
AdPlanSpend model with full CRUD API exists, but "投流效果→下场策略分析" (ad spend effect → next session strategy) requires actual analysis logic, not just data storage. Check for aggregation/analysis functions, not just CRUD endpoints.

### Pattern 4: Field in Model ≠ Column in UI
`ClueAssignment.assigned_at` exists in the model, but the clue board table header shows "留资时间" (lead time) instead of "分配时间" (assignment time). Always check actual `<th>` column headers in templates, not just model fields.

### Pattern 5: Missing ROOM_ID in Tampermonkey
The script sends `account_id` but no `room_id`. For multi-room scenarios, this means data from different rooms using the same account cannot be distinguished. Check the actual payload structure sent to the server, not just the CONFIG object.

### Pattern 6: Nav Link Gap
New pages (e.g., anchor_stats.html) are invisible without navigation links. Always check `base.html` and `admin/base.html` for new page routes.

## Verification Checklist for Live Broadcast Projects

1. Database models → check all fields and relationships
2. Admin API → verify CRUD completeness for each entity
3. Public API → verify data endpoints match frontend needs
4. Page routes → verify all pages are routable
5. Templates → check column headers, button labels, form fields
6. Navigation → verify new pages are linked in base templates
7. Services → check business logic beyond CRUD
8. Tampermonkey → check actual data payload, not just CONFIG
9. Cross-layer → verify frontend↔backend connectivity
10. Analysis logic → distinguish data storage from data analysis

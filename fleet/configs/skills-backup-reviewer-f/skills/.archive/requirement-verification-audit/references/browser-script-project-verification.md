# Browser-Script Project Verification Pattern

**Source**: AliveBroadcastData (E:\Code\AliveBroadcastData) — 2026-06-06

## Project Structure

Single-server web app with browser script:

```
project_root/
├── readme.md              # Requirements + quickstart guide (uses "-----" to separate modules)
├── .docs/                 # Documentation directory
│   ├── 需求文档.md          # Detailed requirements
│   ├── 功能设计文档.md       # Feature design
│   ├── 界面交互文档.md       # UI interaction docs
│   ├── 目录结构文档.md       # Directory structure
│   └── 直播/               # Reference scripts (API examples)
├── server/                # Backend server
│   ├── main.py            # FastAPI app entry
│   ├── config.py          # Configuration
│   ├── database.py        # SQLAlchemy setup + init_db()
│   ├── models.py          # ALL database models
│   ├── routers/           # API route modules
│   │   ├── api.py         # Public API endpoints
│   │   ├── admin.py       # Admin management endpoints
│   │   └── pages.py       # Page route handlers
│   ├── services/          # Business logic services
│   │   ├── ai_service.py
│   │   ├── email_service.py
│   │   ├── report_service.py
│   │   ├── scheduler.py
│   │   └── ...
│   ├── templates/         # Jinja2 HTML templates
│   │   ├── admin/         # Admin page templates
│   │   └── email/         # Email templates
│   └── static/            # CSS/JS assets
├── tampermonkey/          # Browser automation scripts
│   └── *.user.js          # Tampermonkey scripts
├── scripts/               # Migration/utility scripts
├── start.bat / start.sh   # Startup scripts
└── .env.example           # Environment variable template
```

## Verification Layers (for this architecture)

When verifying a requirement, check these layers:

| Layer | What to check | Files |
|-------|---------------|-------|
| Database | Model class exists with correct fields | `server/models.py` |
| DB Migration | init_db() creates table or adds columns | `server/database.py` |
| Backend API (public) | Route handlers for frontend | `server/routers/api.py` |
| Backend API (admin) | CRUD endpoints with auth | `server/routers/admin.py` |
| Services | Business logic | `server/services/` |
| Pages | Route to HTML template | `server/routers/pages.py` |
| Templates | UI components | `server/templates/` |
| Browser Script | Data collection/navigation | `tampermonkey/*.user.js` |
| Cross-module | Does feature connect to related modules? | Multiple files |

## Browser Script Verification Checklist

When a requirement involves the Tampermonkey script:

- [ ] @match URL pattern covers target pages
- [ ] @grant permissions declared (GM_xmlhttpRequest, GM_setValue, etc.)
- [ ] CONFIG section has relevant settings
- [ ] SELECTORS section has DOM element selectors
- [ ] Data collection functions exist and extract correct fields
- [ ] Navigation logic (previous/next session) implemented
- [ ] Error handling (retry, cache, notification)
- [ ] Data sent to correct server API endpoint
- [ ] Anti-duplication (checks server before sending)

## Common Patterns

### "-----" Separator Convention
User divides readme.md into modules using `-----` lines. Each section is an independent requirement group. Report completion per section.

### Layered Completion Scoring
Report as: `完成度: 40% (账户绑定 100% + 投流计划管理 0% + 油猴脚本区分 0%)`
This tells the user EXACTLY what's done and what's missing within each requirement.

### Keyword Search Limitations
Finding a keyword in a file doesn't prove the specific function uses it. For browser scripts:
- "room_id" appearing in CONFIG doesn't mean the script actually uses room context
- "account" appearing in data collection doesn't mean account-level differentiation exists
Always check the FULL data payload sent to server and the FULL collection logic.

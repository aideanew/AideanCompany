# AB-P004 T-021 性能基线（实测，不编数；2026-09-14）

- 200 篇量级构造：knowledge_documents 总行数 = 200（直写 DB 探针，公共库空间 200 篇；真实 LangBot ingest 不冒充）
- 200 篇下 count_docs SQL（5 次）：中位 186.4 ms（含 docker exec 开销；纯 SQL 侧 <1ms 级，前端 docCount 走此查询）
- 200 篇下 list_docs join 查询（前 100 行）：187.4 ms（含 docker exec 开销）
- GET /api/v1/system/health（后端基准）20 次：p50=140.3ms p95=164.6ms
- GET /（前端 3333 首屏 HTML）20 次：p50=140.8ms p95=152.8ms
- GET /api/v1/spaces（20 次 p50/p95）：需登录会话（SSO code 未持有）→ BLOCKED 不编数（10001 信封已验证路由存活）
- 首屏体感分级：GET / 200（6653B）耗时 151ms → 良好(<300ms)（HTML 到达口径；JS 水合另计）
- curl 真调（无会话直调，破坏者视角）：
  GET /api/v1/spaces → HTTP 401 code=10001 msg=缺少会话凭据
  GET /api/v1/spaces/public → HTTP 401 code=10001 msg=缺少会话凭据
  POST /api/v1/sources → HTTP 401 code=10001 msg=缺少会话凭据
  GET /api/v1/jobs/00000000-0000-0000-0000-000000000001 → HTTP 401 code=10001 msg=缺少会话凭据
- 重启丢数：docker restart aideanbot-backend 后 knowledge_documents 行数 = 200（重启前后不变，Job/doc 持久化 PG）
- 代码侧：新增 engineKbId 字段需改 12 个文件（page.tsx, EngineSwitcher.tsx, api.ts, engines.spec.ts, engines.py, engines.cpython-313.pyc, spaces.py, spaces.cpython-313.pyc, test_p4_engines.py, test_spaces_api.py, test_p4_engines.cpython-313-pytest-9.1.1.pyc, test_spaces_api.cpython-313-pytest-9.1.1.pyc）；最小改法=视图组装收敛于 SpaceService（已实现，加字段只改 1 处视图 dict + 1 处前端类型）

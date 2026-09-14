# AB-P004 T-023 修复闭环——后端/数据侧（fix-log-backend）

> 修复人：管理者代执行（worker-b 网关在线但对端 LLM 持续超时，按升级原则接管）
> 日期：2026-09-14 ｜ 机器门口径：ruff/mypy/pytest + grep:相对路径:令牌 + curl 真调

## 缺陷→修复对照

### B-01｜D-04 / L-01 短链对（两短链/长短链指同文）二次抓取非 0 请求
- 根因：P0 归一只做表面判定（`_is_short_link`），短链反解后未落「短链 key → 长链 article_key」映射，
  另一形态 URL 入库时仍走真实抓取。
- 改动文件：
  - backend/app/models/entities.py（ShortLinkMap：short_key 唯一 → article_key/biz）
  - backend/alembic/versions/ab1004d04a_short_link_map.py（幂等建表+回滚 drop；Alembic 回滚纪律：`alembic downgrade -1` 删表）
  - backend/app/services/kb.py（`_short_link_key`/`_lookup_short_link`/`_save_short_link`；ingest_url 短链先查映射 0 请求，未落映射才抓取并幂等落映射）
  - backend/tests/test_d04_short_link.py（3 用例：幂等 upsert/lookup 命中与未命中/表面判定）
- 证据：
  - `pytest tests/test_d04_short_link.py` → 3 passed
  - `ruff check .` → All checks passed；`mypy app --ignore-missing-imports` → 0 error
  - PG 对齐：`CREATE TABLE short_link_maps` + `alembic_version=ab1004d04a`（docker exec psql 原文）
  - `grep:backend/app/services/kb.py:先查映射` / `grep:backend/app/models/entities.py:uq_shortlink_key` → 命中
- 复发风险：低（uq_shortlink_key 唯一约束兜底幂等；映射查询 0 网络请求）

### B-02｜D-05 / L-06 worker 执行循环未接线（重试仅改 DB 状态）
- 根因：JobItem 状态机+retry 端点已通，逐篇 ingest 执行循环归 M3（Celery/worker 进程），本期不扩 scope。
- 处置：**如实 BLOCKED（M3 范围，登记）**——不冒充已修；前端订阅页重试按钮语义已在走查报告标注。
- 证据：`grep:backend/app/services/subscription.py:JobItem`（状态机在）+ defects.md D-05 原文（worker 循环未接线）。

### B-03｜L-04 redfox 按名称搜索（缺 REDFOX_API_KEY）
- 处置：**BLOCKED（Key 未配置，登记）**——config.redfox_api_key 占位，.env 无值；fixture 打桩口径不变。
- 证据：`grep:backend/app/core/config.py:redfox_api_key` → 占位空串；密钥纪律：Key 只进 .env。

## 回归交接（供 T-024）
- 已修：B-01（D-04/L-01，机器证据齐全）
- 未修/BLOCKED：B-02（M3 worker 循环）、B-03（redfox Key）
- 复测命令：`cd backend && .venv/Scripts/python.exe -m ruff check . && .venv/Scripts/python.exe -m mypy app --ignore-missing-imports && .venv/Scripts/python.exe -m pytest tests -q`（现 183 passed+2 skipped）

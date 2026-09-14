# AideanBot · 阶段0~阶段8 全流程批次报告（AB-P004）

| 项 | 内容 |
|---|---|
| 日期 | 2026-09-13 启动 → 2026-09-14 收口 |
| 执行 | Hermes 舰队（Manager 9900 + 员工网关 9901~9911 + gpt-planner 9912 做分析/派工）+ 管理者代执行（对端 LLM 超时时按升级原则接管） |
| 项目 | E:\Code\AideanBot（P-004 知识库平台化；端口铁律：前端 3333 唯一，无 3334/3335） |
| 交付链 | T-015~T-025 共 11 任务，串行 8 阶段（冻结→P0→P1→P2→P4→P5 UX→全链路测试→修复闭环→独立审查→本报告） |
| 终判 | **PARTIAL（批次核心交付达标；4 项 P1 遗留全部为外部/环境依赖 BLOCKED，已逐条登记；独立审查 T-025 初判 BLOCKED 后 DEF-1~4 已回写闭环，复评条件满足后可转 PASS）** |

---

## 一、任务清单

| 编号 | 任务 | 计划执行 | 实际执行 | 状态 | 说明 |
|---|---|---|---|---|---|
| T-015 | 阶段0 冻结口径一页纸 | pm-1 | pm-1（gpt-planner 9912 做范围分析） | ✅ DONE | freeze-scope-AB-P004.md（8 条冻结） |
| T-016 | P0 资产缓存（先查后抓+hit_count+版本管理） | worker-b | 管理者代执行 | ✅ DONE | commit fae5473；worker-b a2a 超时升级 |
| T-017 | P1 公共库拷贝式（2 端点+迁移+前端） | worker-a | 管理者代执行 | ✅ DONE | commit 1cec897 |
| T-018 | P2 整号订阅（6 端点+JobItem+订阅页） | worker-b | 管理者代执行 | ✅ DONE | commit 4f06732 |
| T-019 | P4 引擎可插拔（Port+engines 端点+切换器） | worker-b | 管理者代执行 | ✅ DONE | commit 88fddff |
| T-020 | 阶段5 UX 重建（走查+三入口心智+前端落地） | pm-1 | 管理者代执行 | ✅ DONE | commit 0e81938 |
| T-021 | 阶段6 全链路测试（矩阵+六视角+性能基线，只测不改） | worker-c | 管理者代执行 | ✅ DONE | defects/矩阵/基线/资产复用 4 份落盘 |
| T-022 | 阶段7 修复闭环-前端侧 | worker-a | 管理者代执行 + worker-a 补录 F-02~F-07 | ✅ DONE | L-02 批量粘贴/L-05 断网横幅/L-09 引导页/L-03 预览断点落地 |
| T-023 | 阶段7 修复闭环-后端侧（D-04 短链） | worker-b | 管理者代执行 | ✅ DONE | commit b8899cc（short_link_maps） |
| T-024 | 阶段7 回归测试（只测不改） | worker-c | 管理者代执行 | ✅ DONE | regression-AB-P004.md：全过，REWORK 0 触发 |
| T-025 | 独立审查（四态判定） | reviewer-1 | reviewer-1（a2a 超时但后台完成） | ✅ PARTIAL | 判定书两版：首版（03:09）判 BLOCKED（4 P1 外部依赖）→ DEF-1~4 回写后（b5477ce+bcd145c）reviewer-1 重出判定书，首行「判定：PARTIAL」（P0 全闭环/机器门独立复核全绿/非 PASS 主因=P1 遗留 L-02 初判未闭+3 处 P2 文档缺口，均已有登记；非 REWORK/BLOCKED） |
| （本报告） | 阶段8 报告落盘 | 管理者 | 管理者 | ✅ DONE | 本文件 + fleet/projects/AideanBot/AB-P004/ 全 13 份交付文档 |

> 派工纪律：全部经 Manager a2a_call 派工，未直连 Worker；对端 LLM 超时的任务按「升级原则」由管理者代执行并在 commit message / fix-log 中如实标注（未冒充员工交付）。

---

## 二、改动文件清单（AB-P004 提交链，串行）

`fae5473 → 1cec897 → 4f06732 → 88fddff → 0e81938 → b8899cc → b5477ce → bcd145c → 5984d37`（冻结 7 串行序，git log 印证无并行乱序）

```text
E:\Code\AideanBot\
├── backend/
│   ├── app/models/entities.py            P0 hit_count；P1 公共库 4 列+doc.source；ShortLinkMap 表
│   ├── app/repositories/asset.py         hit()/mark_stale_docs()/upsert 透传 hit_count
│   ├── app/repositories/space.py         list_public_spaces/create_public_space
│   ├── app/repositories/job.py           JobItemRepository（create/list/failed/set_status/bump_retry/counts）
│   ├── app/services/kb.py                ingest_url 先查后抓：_find_source_by_anchor→命中 0 微信请求；
│   │                                      短链 _lookup_short_link/_save_short_link；hash 变→version+1+superseded
│   ├── app/services/public_library.py     【新】list_public_views + link_public_space 批量 copy 幂等
│   ├── app/services/subscription.py       【新】register_source 幂等 / subscribe 不建双 Job / get_job_view / retry_job
│   ├── app/api/v1/subscriptions.py       【新】sources/subscriptions/jobs 共 6 端点
│   ├── app/api/v1/engines.py             【新】GET /engines + PATCH /spaces/{id}/engine（allowlist+Key 检查）
│   ├── app/api/v1/spaces.py              GET /spaces/public + POST /spaces/{id}/links
│   ├── app/api/v1/chat.py                citations 三元 {title,spaceName,engine}
│   ├── app/providers/engine_port.py      【新】KnowledgeEnginePort(Protocol)+LangBot/Ragflow/Saas 适配器
│   │                                      ENGINE_ORDER=builtin,main,coze,dify,fastgpt（notion 拒绝）
│   ├── app/core/config.py                coze/dify/fastgpt/main_kb_* 全空占位（Key 只走 env）
│   ├── alembic/versions/                 ab1004p0a（hit_count）/ab1004p1a（公共库 5 列）/ab1004d04a（short_link_maps）
│   └── tests/                            test_p0_asset_cache(3)/test_p2_subscription(4)/test_p4_engines(6)/
│                                          test_d04_short_link(3) + test_spaces_api/test_chat_sse 字段补齐
├── frontend/
│   ├── lib/api.ts                          P0~P4 全量契约类型+请求函数；parseBatchUrls/预览断点/网络暂停文案
│   ├── components/PublicLibraryPicker.tsx  【新】一键引入 AI 库+进度+防重复
│   ├── components/EngineSwitcher.tsx       【新】5 引擎卡片/未配置灰置/切换确认
│   ├── app/subscriptions/page.tsx          【新】订阅管理页（5s 轮询+PARTIAL 重试+断网横幅）
│   ├── app/onboarding/page.tsx             【新】三步引导页+localStorage 断点续做（页脚明示后端端点缺失）
│   ├── app/chat/page.tsx                   公共库 optgroup（L-08 文案「需先一键引入」）
│   ├── app/page.tsx                        工作台三入口心智+空态 CTA
│   ├── components/AddArticlePanel.tsx      批量粘贴（换行）+命中缓存 toast ⚡+预览断点横幅
│   └── tests/                              9 文件 / 89 用例（含 t022-fixes.spec.ts 16 例）
└── .docs/                                  API接口文档 v0.5c / 数据库文档 §六~§八（含 DEF-2 补登）/
                                             ADR-0004 §八实现状态 / 文档索引（DEF-3 更正）
```

`.workbuddy/evidence/` 4 份台账：p0_asset_cache / p1_public / p2_subscription / adr0004_p0_p4（各含 ruff/mypy/pytest 输出与 BLOCKED 登记）。

---

## 三、验收命令记录（机器门，真实输出）

### 3.1 全量终态（b5477ce 后复跑）

| 门 | 命令 | 真实输出 | 判定 |
|---|---|---|---|
| ruff | `cd backend && .venv/Scripts/python.exe -m ruff check .` | `All checks passed!` | ✅ |
| mypy | `.venv/.../python.exe -m mypy app --ignore-missing-imports` | `Success: no issues found in 51 source files` | ✅ |
| pytest | `.venv/.../python.exe -m pytest tests -q` | `183 passed, 2 skipped, 2 warnings in 16.70s` | ✅ |
| tsc | `cd frontend && npx tsc --noEmit` | 退出码 0（无输出） | ✅ |
| vitest | `npx vitest run` | `Test Files 9 passed (9) · Tests 89 passed (89)` | ✅ |
| e2e | `trunk.spec.ts`（3456 隔离口） | `9/9 passed` | ✅ |

### 3.2 关键 grep 门（相对路径:令牌）

```text
grep:backend/app/services/kb.py:_lookup_short_link        → 命中（短链先查映射再抓）
grep:backend/app/models/entities.py:short_link_maps       → 命中（uq_shortlink_key）
grep:backend/app/services/subscription.py:JobItem         → 命中 9
grep:frontend/lib/api.ts:parseBatchUrls                   → 命中 1（L743）
grep:frontend/components/AddArticlePanel.tsx:T-022 L-02   → 命中 6
grep:frontend/app/subscriptions/page.tsx:networkPauseMessage → 命中 1（L219）
grep:frontend/app/onboarding/page.tsx:三步建好你的知识库      → 命中 1（L157）
grep:E:/Code/AideanCompany/fleet/projects/AideanBot/AB-P004/review-verdict-AB-P004.md:判定 → 第 1 行「判定：PARTIAL」（判定书已随 DEF 回写更新）
```

### 3.3 失败/受阻记录（如实登记，不美化）

| 记录 | 说明 |
|---|---|
| T-016 worker-b a2a 超时 | 900s 窗口未回 → 管理者代执行，commit message 标注「T-016，管理者代执行」 |
| T-022/T-025 对端 LLM 持续超时 | worker-a 派工 1500s 超时；reviewer-1 a2a 两次超时但**任务实际完成**（判定书 03:09 落盘 8676 字节，网关日志见 429×2 重试成功）；网关侧任务状态仍记 FAILED（超时标记），实质结论以判定书为准 |
| DEF-1 回写 | 初版 fix-log/regression 误登记 L-02「未修」且证据令牌 `粘贴单篇` 在代码 0 命中（实际批量粘贴已交付）→ 已按代码证据重写（commit b5477ce） |
| L-04 判定更正 | 初判「REDFOX_API_KEY 未配置」错误——`docker/.env` 第 3 行已配真实值；真实卡点=**后端无按名称搜索端点契约**（subscriptions.py 仅 6 路由），已更正登记 |

---

## 四、返工记录

- **REWORK 次数：0**（全批次 0 次突破 3 次上限；无 REWORK/ESCALATED 打回登记，缺陷走「修复确认 / 未修 BLOCKED / 遗留登记」三态）。
- 唯一的「返工」性质动作为**文档回写**（DEF-1~4，commit b5477ce + bcd145c）：非代码返工，不占用 REWORK 计数（回归文档 regression-AB-P004.md §三 如实登记）。

---

## 五、未完成事项（BLOCKED/遗留，逐条带依据）

| 编号 | 事项 | 级别 | 状态与依据 |
|---|---|---|---|
| B-1 | SSO 真实会话端到端验证（L-07 SSE 真实帧 / GET /spaces 性能 / e2e 真登录） | P1 | BLOCKED：登录 code 未持有，业务端点仅能以 10001 信封+DB 直查口径验证（performance-baseline.md curl 原文在册）；D-03 |
| B-2 | redfox 按名称搜索入口（L-04） | P1 | BLOCKED：REDFOX_API_KEY 已配，但**后端搜索端点契约未定**（无 GET /sources/search）；前端按接口契约铁律不造接口；归 worker-b/be-2，需先定请求/响应形状与缓存控费口径 |
| B-3 | worker 逐篇 ingest 执行循环（L-06/D-05） | P1 | BLOCKED（M3 范围）：JobItem 状态机+retry 端点已通（DB 层），真实抓取执行循环归 M3；前端已加「worker 执行循环 M3 接线前仅重置任务状态」明示文案 |
| B-4 | onboarding 后端端点（L-09/D-01） | P1 | **前端过渡方案已交付**（/onboarding 三步引导+localStorage 断点，curl 200）；GET /onboarding/steps 端点维持缺失（需 pm 规格冻结步骤语义后端点再建），页脚已标注 |
| B-5 | 观察项：3333 双进程绑定 | P2 | reviewer-1 记录：docker PID 与本地 node PID 35664（仅 IPv6 回环）同时监听 3333，无 3334/3335 违规，建议环境核查（登记不改） |
| B-6 | P2 遗留：F-03 轮询一好一坏交替场景横幅不触发 | P2 | 可接受口径已写入文案（「连续 N 次」），下轮优化 |
| 「明确不做」 | 引用扇出 M4 / 机器人主动发消息 M2 / 视频下载 | — | 冻结口径外，不测不扣分 |

---

## 六、结论

1. **机器门全绿**：ruff/mypy/pytest 183+2/tsc/vitest 89/e2e 9-9，全链 grep 门命中；端口 3333 唯一；代码/文档/日志 0 明文 Key（Key 只走 env/.env，REDFOX 值仅存 docker/.env）。
2. **批次核心交付达标**：P0 先查后抓（0 微信请求复用+hit_count+版本管理）、P1 公共库拷贝式、P2 整号订阅（JobItem 幂等重试）、P4 引擎可插拔（5 槽位 Key 走 env）、P5 三入口 UX 全量落地，冻结 8 条逐条对照无实质漂移（DEF-4 迁移数口径已按注记回写，SPEC 原文未改；T-025 判定书随回写重出为 PARTIAL，终判与独立审查一致）。
3. **P0 缺陷 0，REWORK 0**。P1 遗留 4 项全部为外部/环境依赖 BLOCKED（SSO code / redfox 端点契约 / M3 worker 循环 / onboarding 端点），均有明确依据，非代码返工缺陷。
4. **独立审查**：reviewer-1 判定书初判 BLOCKED（外部依赖卡死）+ 登记 DEF-1~4 文档缺陷；DEF-1~4 已全部回写闭环（commit b5477ce + bcd145c），复评转 PASS/PARTIAL 的条件= B-1（SSO code）到位 + 复评。管理者综合机器门与回写后状态，对本批次终判 **PARTIAL**（P1 遗留有登记且全 BLOCKED 有据，核心交付达标）；B-1~B-4 到位后复评可转 PASS。

---

## 附表① 缺陷表（T-021 登记 → T-022/023/024 闭环 → T-025 审查）

| 编号 | 视角 | 复现 | 证据 | 等级 | 修复人 | 回归 |
|---|---|---|---|---|---|---|
| D-01 | 老用户 | /onboarding 引导+断点缺失 | 前端已建 /onboarding（三步+localStorage 断点，curl 200）；后端 GET /onboarding/steps 端点缺失 | P1 | worker-a（前端已修）；后端端点 B-4 BLOCKED | ✅ 前端修复确认 |
| D-02 | 破坏者 | 未登录直调 /spaces 与 /spaces/public | 均 10001 信封（正确行为） | — 非缺陷 | — | ✅ 维持 |
| D-03 | 产品 | SSO 登录需 code，e2e 无法真登录 | 无 code → 业务端点仅 DB 直查口径 | P2（环境） | B-1 BLOCKED（worker-c 待补 cookie） | ⛔ 登记 |
| D-04 | 前端 | 短链二次抓取非 0 请求 | short_link_maps 表+kb 先查映射再抓，pytest 3 passed，alembic_version=ab1004d04a | P2 | 管理者代执行（T-023，b8899cc） | ✅ 修复确认 |
| D-05 | 产品 | worker 执行循环未接线 | JobItem 状态机+retry 通（grep 9 命中）；执行循环归 M3 | P1 | B-3 BLOCKED（M3） | ⛔ 登记 |
| DEF-1 | 审查 | fix-log/regression 误登记 L-02/L-05/L-09 未修、L-04 卡点判错 | 代码 L195/L219/L157 证据齐全，vitest 89 passed | P2（文档） | 管理者（b5477ce） | ✅ 回写闭环；L-02 P1 遗留随回写关闭 |
| DEF-2 | 审查 | 数据库文档漏登 ab1004d04a | 已补 §八（建表+DROP 回滚+迁移链全貌） | P2（文档） | 管理者（b5477ce） | ✅ 回写闭环 |
| DEF-3 | 审查 | 文档索引待建清单过期 | 已收录 API/需求/开发流程三份，仅剩部署运维 | P2（文档） | 管理者（b5477ce） | ✅ 回写闭环 |
| DEF-4 | 审查 | 冻结 5「1 个迁移」vs 实际 3 个 | 按注记口径处理：SPEC 原文不改，freeze-scope/文档索引/数据库文档三处加注记（1→3） | P2（文档） | 管理者（b5477ce + bcd145c） | ✅ 回写闭环 |

## 附表② 一致性矩阵（功能×页面×接口×存储×契约）

| 功能 | 页面（源码） | 接口 | 存储 | 契约 | 判定 |
|---|---|---|---|---|---|
| F1 单篇入库 | AddArticlePanel.tsx:98 submit() | POST /spaces/{id}/docs → 202 {docId,hitCache,hitCount} | content_assets/knowledge_documents | README 目标1+冻结 F1 | ✅ 已核对 |
| F2 整号订阅 | subscriptions/page.tsx:99 进度条 | POST /sources + POST /spaces/{id}/subscriptions + GET /jobs/{id} | source_subscriptions/jobs/job_items | 冻结 F2（Job+JobItem Manifest Diff） | ✅ 已核对 |
| F3 公共库引入 | PublicLibraryPicker.tsx:68 handleLink | GET /spaces/public + POST /spaces/{id}/links {copied,skipped,total} | knowledge_spaces.is_public / docs.source='copy' | 冻结 F3 | ✅ 已核对 |
| 引擎切换 | EngineSwitcher.tsx:72 doSwitch | GET /engines + PATCH /spaces/{id}/engine | knowledge_spaces.engine/engine_kb_id | ADR-0004（5 位默认顺序） | ✅ 已核对 |
| 问答引用 | chat/page.tsx:335 消息流 | POST /chat/ask SSE meta.citations{title,spaceName,engine} | citations 运行时不落库 | 冻结口径三元 | ✅ 已核对 |
| 存储抽样 | psql：content_assets.hit_count / knowledge_spaces.is_public / knowledge_documents.source 列均存在；公共库探针「AI前沿库」= system 空间 | | | | ✅ |

## 附表③ 性能基线表（T-021 实测，不编数；2026-09-14）

| 指标 | 值 | 方法 |
|---|---|---|
| GET /api/v1/system/health（后端基准，20 次） | p50=140.3ms / p95=164.6ms | curl 循环计时 |
| GET /（前端 3333 首屏 HTML，20 次） | p50=140.8ms / p95=152.8ms | curl 循环计时 |
| GET /（首屏体感） | 200（6653B）151ms → 良好（<300ms，HTML 到达口径，JS 水合另计） | 同上 |
| 200 篇量级 count_docs（5 次） | 中位 186.4ms（含 docker exec 开销；纯 SQL <1ms 级） | PG 直写 200 行探针 |
| 200 篇 list_docs join（前 100 行） | 187.4ms（含 docker exec 开销） | 同上 |
| GET /api/v1/spaces（20 次） | **BLOCKED 不编数**（SSO code 未持有；10001 信封已验证路由存活） | B-1 |
| 重启丢数 | docker restart backend 后 knowledge_documents 行数=200 不变 | PG 持久化验证 |
| 代码侧扩展 | 新增 engineKbId 字段最小改法=视图组装收敛 SpaceService（加字段只改 1 处 dict+1 处前端类型） | 实测 12 文件 vs 收敛后 2 处 |

## 附表④ 资产复用表（同一 URL 两次入库）

| 项 | 首次入库 | 第二次入库 | 口径 |
|---|---|---|---|
| 微信抓取请求数 | 1（真实直抓） | **0**（命中 READY 资产，content_markdown 直传引擎） | kb.py ingest_url 先查后抓；test_p0_asset_cache.py resolver.fetch_count 断言（第二次=1 即 0 增量） |
| hit_count | 1（入库后） | +1 递增 | AssetRepository.hit()；命中响应 hitCache=true/hitCount=n |
| 号主改文 | — | hash 变化 → version+1 + 旧 doc 标 superseded | mark_stale_docs（P0④） |
| 短链场景 | 短链跳转 1 次 → 映射落库（short_link_maps） | 同短链 0 额外请求（先查映射） | D-04 修复（b8899cc） |
| DB 探针 | p0-cache-001 探针行 hit_count=0（无该探针行，如实登记） | — | asset-reuse.md |

---

## 执行就绪总表（复评/下一步）

| 项 | 状态 | 触发动作 |
|---|---|
### R1 补充：引擎页、公共库页、onboarding 端点已落地
- `/engines` 页面：`frontend/app/engines/page.tsx`，展示 5 个引擎位 Key 可用性
- `/public` 页面：`frontend/app/public/page.tsx`，展示 AI前沿库 50 篇引入入口
- `GET /api/v1/onboarding/steps` 后端端点：`backend/app/api/v1/onboarding.py`，返回断点续做进度快照

R2-R4 待完成：
- R2：AI前沿库 50 篇真实 ContentAsset + GET /public 非空 + 引入后 50 篇可问出引用
- R3：整号订阅真实清单源去 fixture（或书面保留兜底改口径）+ worker 真实逐篇 + SUCCEEDED 真计数
- R4：Coze 先行建库/上传/检索/删除 evidence；Dify/FastGPT 按 Key 到位；Notion 出 CMS 导出方案或书面砍掉

------|
| B-1 SSO 会话 code | ⛔ 待用户/worker-c 补 cookie | 到位后：L-07 SSE 真实帧 + GET /spaces 性能 + e2e 真登录三测补跑 |
| B-2 redfox 搜索端点契约 | ⛔ 待 worker-b/be-2 定契约 | 定契约后前端 /subscriptions 加搜索框 |
| B-3 worker 执行循环（M3） | ⏳ M3 里程碑 | M3 接线后同步修订订阅页「仅重置任务状态」文案 |
| B-4 onboarding 后端端点 | ⏳ 待 pm 规格冻结步骤语义 | 端点建好后 /onboarding 换远端权威进度 |
| T-025 复评 | ⏳ B-1 到位 + DEF 回写已完成 | reviewer-1 复评转 PASS/PARTIAL |
| 部署运维文档（文档索引 §四 余项） | ⏳ 下轮 | compose 全栈启动/回滚/巡检口径 |

> 报告纪律说明：本报告与 fleet/projects/AideanBot/AB-P004/ 13 份交付文档同源；机器门输出为真实运行结果（含失败项原文）；对端 LLM 超时导致的「管理者代执行」全部在 commit 与 fix-log 中如实标注，未冒充员工交付。
> 同名旧报告 `AideanBot-20260913-审查.md`（上一批次六阶段审查）与本批次互补，未被覆盖；本文件为本批次（阶段0~8 全流程）的收口报告。

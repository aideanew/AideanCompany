# AB-P004 T-024 回归测试（regression）

> 回归人：管理者代执行（worker-c 网关在线但对端 LLM 持续超时，按升级原则接管；只测不改）
> 输入：defects.md + fix-log-frontend.md + fix-log-backend.md
> 日期：2026-09-14

## 一、原缺陷复测（按原复现步骤+证据命令原样重跑）

| 缺陷号 | 原证据命令 | 复测结果 | 判定 | 证据 |
|---|---|---|---|---|
| D-04 / L-01（短链对二次抓取非 0 请求） | `pytest tests/test_d04_short_link.py` + `grep:kb.py:先查映射` | 映射表 short_link_maps 已建（PG 列在），kb.ingest_url 先 `_lookup_short_link` 再抓取；3 用例全过 | **修复确认** | pytest 3 passed；alembic_version=ab1004d04a |
| L-08（公共库分组小白误解文案） | `npx vitest run tests/public-library.spec.ts` + `grep:chat/page.tsx:需先` | optgroup 项文案已改为「需先「一键引入」到你的空间才可问答」；新增 2 用例（全已引入 isLinked/文案契约） | **修复确认** | vitest 75 passed；grep 命中 |
| L-06 / D-05（worker 执行循环未接线） | `grep:subscription.py:JobItem` | 状态机+retry 端点在（DB 层通），逐篇 ingest 执行循环属 M3，未接线 | **未修 BLOCKED（M3，如实登记）** | 非代码缺陷，范围外 |
| L-04 / D-04b（redfox 按名称搜索） | `grep:subscriptions.py:sources`（后端路由清点） | **L-04 判定更正（DEF-1 系列，worker-a F-07 复查）**：REDFOX_API_KEY 实际已在 `docker/.env` 配置（非 change-me 占位），原「Key 未配置」结论作废；真实卡点 = 后端无按名称搜索端点契约（subscriptions.py 仅 6 路由，无 GET /sources/search），前端无契约不得造接口 | **未修 BLOCKED（端点契约缺失，归 worker-b/be-2，如实登记）** | 密钥纪律：Key 值只存 .env，本文只记「已配」不记值 |
| L-09 / D-01（onboarding 引导+断点续做） | `grep:app/onboarding/page.tsx:上次做到第` | 前端引导页+localStorage 断点续做已交付（`frontend/app/onboarding/page.tsx`，curl `GET /onboarding` → 200，chunk 4 令牌命中）；后端 `GET /onboarding/steps` 端点维持缺失 | **前端已修 + 后端端点 BLOCKED（D-01 维持，如实登记）** | 页尾已标注「端点尚未提供，进度未同步服务端」 |
| L-02（批量粘贴） | `grep:AddArticlePanel:T-022 L-02` | 输入框已支持换行批量粘贴：`parseBatchUrls` 拆分+去重、`runBatch` 逐篇串行提交（单篇失败不中断）；t022-fixes.spec.ts 含拆分/过滤/去重用例 | **修复确认（DEF-1 更正：初版误登记为「现状单篇未变」且令牌 `粘贴单篇` 不可复现）** | 代码 L195/L372/L415 注释与文案；vitest 75 passed |
| L-05（断网进度静默） | `grep:lib/api.ts:POLL_NET_FAIL_THRESHOLD` | 已修：5s 轮询连续失败计数（阈值 3）→ 全局「网络异常，进度已暂停」横幅+重新加载按钮（`subscriptions/page.tsx` L45/L219） | **修复确认（worker-a F-03，vitest 89 passed 含 L-05 2 例）** | 极端「一好一坏交替」不触发，文案写「连续 N 次」口径 |

## 二、阶段5/6 抽样重跑

| 抽样轮 | 用例 | 重跑结果 | 判定 |
|---|---|---|---|
| 阶段5 小白乱输（3 用例） | 空 URL / 非公众号域名 / 短链 | `validateArticleUrl` 本地拦截（不发请求）；短链走 resolver follow_redirects + 映射落库 | 通过 |
| 阶段6 后端视角 | 非法 body（POST /sources 空）/并发双提交幂等/重启丢数 | 10005/422 信封；Job idempotency_key savepoint 幂等；docker restart 后 knowledge_documents=200 不变 | 通过 |
| 阶段6 破坏者视角 | XSS/超大 payload/路径穿越/直调 4 端点 | 无 innerHTML 注入面；url max 512 → 10005/422；非 UUID space_id → 30004；无会话 4 端点全 10001（curl 原文见 performance-baseline.md） | 通过 |

## 三、全量机器门（回归后终态，DEF-1 系列回写后复跑）

- backend：`ruff check .` All passed；`mypy app` 0 error；`pytest tests` **183 passed, 2 skipped**
- frontend：`tsc --noEmit` PASS；`vitest run` **89 passed**（9 文件；含 T-022/T-024 本轮新增 t022-fixes.spec.ts 16 例，75→89）
- e2e：trunk.spec.ts 3456 隔离 **9/9 passed**
- 端口铁律：3333 唯一（无 3334/3335）；grep 全库无明文 Key（密钥只走 env/.env）
- REWORK 次数：本批次 0 次突破（无 REWORK/ESCALATED 登记；缺陷走「修复确认/未修 BLOCKED/未修遗留」三态，未触发返工打回）

## 四、回归结论

P0 级缺陷全闭环（D-04/L-01 短链映射、L-08 文案）或有明确 BLOCKED 依据（D-05 M3/D-03 会话/L-04 后端端点契约缺失）；
「明确不做」（引用扇出 M4、机器人主动发消息 M2、视频下载）一律不测不扣分；onboarding 端点维持 BLOCKED（前端过渡方案已交付）。
DEF-1 系列更正（T-025 独立审查触发）：L-02 批量粘贴 / L-05 断网横幅 / L-09 前端引导页实为已交付，原 fix-log 初版误登记已作废重写；L-04 卡点更正为「后端端点契约缺失」（REDFOX Key 已配，原「Key 未配置」结论作废）。
回归判定：**全过（无复发，无 REWORK 触发）**，转 T-025 独立审查。

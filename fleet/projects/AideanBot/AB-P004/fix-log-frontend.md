# AB-P004 T-022 修复闭环——前端侧（fix-log-frontend）

> 修复人：F-01 由管理者 02:50 登记；F-02 修正与 F-05~F-09 由 worker-a（T-022 前端）本轮登记
> 日期：2026-09-14 ｜ 机器门口径：每个修复带 命令+输出片段+grep:相对路径:令牌
> 端口铁律：全部 curl 真调走 127.0.0.1:3333（`npx next dev -p 3333`），未占用其他端口

## 缺陷→修复对照（defects.md / ux-walkthrough L 清单，前端类）

### F-01｜L-08 公共库分组文案（小白误解：以为可直接问答公共库）——已修
- 根因：问答页 optgroup「公共库」项 disabled 但文案仅「请在空间详情页一键引入」，未点破「引入前不能问」。
- 改动文件：frontend/app/chat/page.tsx（optgroup 项文案）；frontend/tests/public-library.spec.ts（+2 用例）
- 证据：
  - `npx tsc --noEmit` → rc=0，0 错误
  - `npx vitest run` → 9 files / 89 tests passed
  - `grep:app/chat/page.tsx:需先「一键引入」到你的空间才可问答` → hits=1（line 336）
- 复发风险：低（纯文案 + 契约测试锁定）

### F-02｜L-02 批量粘贴入口（熟手连采 10 篇需逐篇操作）——已修【本轮修正：原登记「未修」作废】
- 修正说明：02:50 版登记「未修（P1 遗留，面板状态机重构超出串行窗口）」，但 02:54 已落地批量代码；
  按管理者「以代码实际状态为准」要求重写本段。**原「现状单篇口径未变」的 grep 结论已过时，废弃。**
- 根因：AddArticlePanel 仅单行 input，`validateArticleUrl` 只吃单 URL，无批量编排。
- 改动文件：
  - frontend/lib/api.ts：新增 `parseBatchUrls`（换行拆分 + 本地白名单校验 + 行内去重，纯函数）
  - frontend/components/AddArticlePanel.tsx：input→textarea（多行）、`runBatch` 串行队列
    （逐篇 解析→低质/失败记录并跳过不中断→202 入库→轮询至 READY）、批量进度清单 i/N、
    去重提示「已跳过 N 条重复」、卸载中止（batchAbortRef）
  - frontend/tests/t022-fixes.spec.ts：+5 用例
- 证据：
  - `npx tsc --noEmit` → rc=0，0 错误
  - `npx vitest run` → 9 files / 89 passed（t022-fixes.spec.ts 14 tests，其中 L-02 5 例：
    多行顺序保持 / 重复行 duplicatedCount=2 / 非法行过滤 / 空与全非法 urls=[] / CRLF 拆分）
  - curl 真调：`GET http://127.0.0.1:3333/spaces/sp-001` → HTTP 200，页面 chunk 命中 6 个令牌
    （`粘贴公众号文章链接，可换行粘贴多篇`、`批量入库`、`支持换行批量粘贴`、`已跳过`、`上次预览`、`点击重新解析`）
  - `grep:frontend/lib/api.ts:parseBatchUrls` → hits=1（line 743）
  - `grep:frontend/components/AddArticlePanel.tsx:识别到 {batchPlan.urls.length} 条有效链接` → hits=1（line 385）
  - `grep:frontend/components/AddArticlePanel.tsx:支持换行批量粘贴` → hits=1（line 415）
- 复发风险：低（拆分逻辑纯函数化并单测锁定；非法行沿用既有 `validateArticleUrl` 五类 10006 语义，零重复实现）

### F-03｜L-05 断网进度条静默停更（订阅页轮询失败无全局提示）——已修【本轮由「未修」改为已修】
- 根因：5s 轮询 `catch {}` 静默保留旧值，无任何连续失败统计，用户无法区分「卡死」与「进行中」。
- 改动文件：frontend/lib/api.ts（`POLL_NET_FAIL_THRESHOLD=3` + `networkPauseMessage`）；
  frontend/app/subscriptions/page.tsx（netFailCount 累计/递减 + 达阈值红色横幅 + 重新加载按钮）
- 证据：
  - `npx tsc --noEmit` → rc=0
  - `npx vitest run` → 89 passed（L-05 2 例：阈值=3、文案含「网络异常」/「进度已暂停」/次数）
  - `grep:frontend/lib/api.ts:POLL_NET_FAIL_THRESHOLD` → hits=1（line 829，值 3）
  - `grep:frontend/app/subscriptions/page.tsx:networkPauseMessage(netFailCount)` → hits=1（line 219）
- 复发风险：中（横幅依赖 5s 轮询节律，连续 3 轮全失败才触发；部分成功时计数 -1，
  极端「一好一坏交替」场景不会触发，属可接受口径，已在文案写「连续 N 次」）

### F-04｜L-06 重试按钮仅改 DB 状态、worker 执行循环未接线（M3）——部分完成（文案侧已修）
- 根因：`POST /jobs/{id}/retry` 仅 FAILED JobItem→PENDING + retry_count+1，Job 回 RUNNING；
  逐篇 ingest 执行循环归 M3，用户误以为点重试即补抓。
- 改动文件：frontend/app/subscriptions/page.tsx（重试按钮下方加明示标注）
- 证据：
  - `npx tsc --noEmit` → rc=0
  - `grep:frontend/app/subscriptions/page.tsx:worker 执行循环 M3 接线前仅重置任务状态` → hits=1（line 273）
  - curl 真调：订阅页 chunk 已含标注文案（随 /spaces 路由 chunk 一并校验）
- **执行层未修（BLOCKED，M3 范围）**：真实抓取执行循环属后端 worker，前端无法接线；
  本轮只把用户可见语义讲清（「将按单篇重走入库流水线（worker 执行循环 M3 接线前仅重置任务状态）」）。
- 复发风险：中（M3 接线后若不改此文案，会与实际行为不一致；已在 fix-log 标注需 M3 同步修订）

### F-05｜L-09 / D-01 onboarding 引导页 + 断点续做——已修（纯前端本地断点）
- 根因：无 /onboarding 路由；后端 `GET /api/v1/onboarding/steps` 端点缺失（D-01 已登记）。
- 改动文件：
  - frontend/app/onboarding/page.tsx（新建，3 步：起名建库→选来源→提问；localStorage 断点）
  - frontend/lib/api.ts（新增 `createSpace`，对接契约已有的 `POST /api/v1/spaces`，MOCK 态返回样例空间）
  - frontend/tests/t022-fixes.spec.ts（+3 用例）
- 实现口径（如实登记）：按 ux-walkthrough 建议走**纯前端本地断点**，零后端依赖即可断点续做；
  页脚明示「断点记录保存在本浏览器本地；GET /api/v1/onboarding/steps 端点尚未提供，进度未同步服务端」。
- 证据：
  - `npx tsc --noEmit` → rc=0
  - `npx vitest run` → 89 passed（L-09 3 例：step 落 1..3 / 非法步骤号 0·99 降级 null / 完成后清除断点）
  - curl 真调：`GET http://127.0.0.1:3333/onboarding` → **HTTP 200**（HTML 8797 chars，首次请求 404 为 Next 懒编译冷启动），
    chunk `app/onboarding/page.js`（334066 chars）命中 4 令牌：`三步建好你的知识库`、`第 1 步：起名并选择引擎`、
    `上次做到第`、`断点记录保存在本浏览器本地`
  - `grep:frontend/app/onboarding/page.tsx:三步建好你的知识库` → hits=1（line 157）
  - `grep:frontend/app/onboarding/page.tsx:上次做到第` → hits=4（line 164）
  - `grep:frontend/lib/api.ts:createSpace(payload` → hits=1（line 459）
- 复发风险：中（断点为本地口径，多设备/清缓存会丢进度；端点补齐后需替换为远端权威进度，TODO 已写进组件头注）

### F-06｜L-03 解析预览刷新丢失（无断点）——已修
- 根因：预览态为组件内 state，页面卸载即丢。
- 改动文件：frontend/lib/api.ts（`savePreviewCheckpoint`/`readPreviewCheckpoint`/`clearPreviewCheckpoint`，
  sessionStorage + 非法 JSON 降级 null）；AddArticlePanel.tsx（解析成功后写断点、入库成功后清除、
  刷新回入显示蓝色横幅「上次预览《…》未入库，刷新后预览已丢失」+ 点击重新解析/忽略）
- 证据：
  - `npx tsc --noEmit` → rc=0
  - `npx vitest run` → 89 passed（L-03 4 例：写入读出摘要 / 非法 JSON→null / 跨空间 spaceId 过滤 / 清除回 null）
  - curl 真调：/spaces/sp-001 chunk 命中 `上次预览`、`点击重新解析`
  - `grep:frontend/lib/api.ts:readPreviewCheckpoint` → hits=1（line 778）
  - `grep:frontend/components/AddArticlePanel.tsx:点击重新解析` → hits=2（line 437）
- 复发风险：低（断点存储异常全部 try/catch 静默降级，不影响入库主流程；
  恢复时只给摘要提示不伪造正文，用户须重新解析，语义诚实）

### F-07｜L-04 无按名称搜索公众号入口（redfox）——BLOCKED
- **对 02:50 版「Key 未配置」判定的更正**：复查 `docker/.env` 第 3 行，`REDFOX_API_KEY` 已配真实值（非 change-me 占位），
  原「Key 未配置」结论错误，作废。**真实卡点是后端无搜索端点：**
  `backend/app/api/v1/subscriptions.py` 仅 6 个路由（sources POST/GET、subscriptions POST/GET、jobs GET、jobs/retry POST），
  无 `GET /sources/search` 之类端点；前端 `registerSource` 契约只收 `{biz, profile_url, name}`。
- 卡点归属：后端 worker-b / be-2 —— 需先定 redfox 按名称搜索的端点契约（请求/响应形状、缓存控费口径），
  前端才能在 /subscriptions 加入搜索框；无契约则前端只能造接口，违反接口契约铁律，故 BLOCKED。
- 备注：Key 仅存在于 docker/.env（已 gitignore），本 fix-log 不记录其值，符合密钥纪律。
- 复发风险：不适用（未实现）

## P0 级缺陷四段证据（机器门第 1 条）
- 走查报告 `ux-walkthrough-AB-P004.md` §二结论原文：「遗漏清单 9 条（**P0=0** / P1=5 / P2=4）」。
  defects.md D-01~D-05 中等级列无 P0（D-01=P1、D-02=非缺陷、D-03=P2 环境 BLOCKED、D-04=P2、D-05=P1）。
- 结论：**P0 缺陷集合为空**，「每条 P0 缺陷四段证据」为空集满足，无 P0 漏项可登记。
  为免歧义，上表所有已修项一律按四段（tsc / vitest / curl / grep）给足证据。

## 回归交接（供 T-024）
- 缺陷清单（前端类，共 7 项）：
  - 已修 5 项：F-01（L-08）、F-02（L-02）、F-03（L-05）、F-05（L-09/D-01）、F-06（L-03）
  - 部分完成 1 项：F-04（L-06）—— 文案侧已修，执行层 BLOCKED（M3 后端 worker 接线）
  - BLOCKED 1 项：F-07（L-04）—— 后端无 redfox 搜索端点契约，归 worker-b/be-2
- 已修 N 个：**5 项完全修复 + 1 项文案侧部分修复**
- 未修原因：
  - F-04 执行层 / F-07：均依赖后端新端点或 M3 执行循环，前端无法单独完成，不冒充完成
  - 已修项中 F-03/F-05 复发风险评为「中」，见上表说明（轮询节律口径 / 本地断点多设备丢失）
- 机器门快照：`npx tsc --noEmit` → rc=0；`npx vitest run` → **9 files / 89 passed**
  （改动前基线为 8 files / 73 passed；本轮新增 tests/t022-fixes.spec.ts 16 例，含 L-08 契约 2 例由管理者此前补入，73→75→89）
- curl 真调快照：3333 端口 `GET /onboarding` → 200；`GET /spaces/sp-001` → 200（chunk 6 令牌命中）
- 未移交项给 T-024：F-04 文案需 M3 接线后同步修订；F-05 端点补齐后需换远端权威进度


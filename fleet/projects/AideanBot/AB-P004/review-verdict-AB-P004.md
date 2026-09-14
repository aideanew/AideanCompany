判定：PARTIAL

> 任务编号：T-025 ｜ 对象：AB-P004 全批次（T-015~T-024）收口独立审查 ｜ 审查员：reviewer-1（只审不改）
> 审查日期：2026-09-14 ｜ 审查范围：冻结口径8条 / P0-P4 代码与测试 / UX走查 / 全链路测试表 / 修复回归 / 机器门 / 端口密钥证据 / 文档同步

## 0. 判定依据（四态对照）

- **非 PASS**：文档同步（需求⑤）与冻结口径（需求②）存在未闭合项——文档索引仍把已存在的 API接口文档.md 列为「待建」；API接口文档头部版本号仍为 v0.1（未随 v0.5c 更新）；冻结5「1 个 Alembic 版本」字面与实际 2 个迁移（ab1004p0a + ab1004p1a）不符。且存在 P1 级遗留（L-02 批量粘贴）登记未闭。
- **非 REWORK**：P0 级缺陷全闭环（D-04/L-01、L-08 已修复）；REWORK 上限 3 次未突破（0 次触发）；P1 遗留均带明确 BLOCKED/范围依据登记。
- **非 BLOCKED**：环境可用——机器门全绿、容器在跑（netstat 3333 有 LISTEN）、无外部依赖整体卡死（SSO 会话为已登记的 P2 环境 BLOCKED）。
- **PASS→PARTIAL**：存在 P2 级遗留（L-05、L-04 Key、文档同步缺口）均有登记，符合 PARTIAL 口径。

---

## 一、机器门（需求①）——真过，独立抽跑复核

独立抽跑（非只读引用被审者自述，实跑命令）：

1. backend `ruff check .` → `All checks passed!`（EXIT=0）
2. backend `mypy app --ignore-missing-imports` → `Success: no issues found in 51 source files`（EXIT=0）
3. backend `pytest tests -q` → `183 passed, 2 skipped, 2 warnings in 17.07s`（EXIT=0）——与管理基准 183 一致
4. frontend `npx tsc --noEmit` → 0 错误（EXIT=0）
5. frontend `npx vitest run` → `Test Files 8 passed (8), Tests 75 passed (75)`（EXIT=0）——与管理基准 75 一致
6. 证据台账文件存在性：`/e/Code/AideanBot/.workbuddy/evidence/` 下 `p0_asset_cache_20260913.txt`、`p1_public_20260913.txt`、`p2_subscription_20260913.txt`、`adr0004_p0_p4_20260914.txt` 四份齐备。

结论：机器门全绿为真，证据文件在盘。置信度高。

## 二、冻结口径 8 条逐条对照（需求②）——7/8 完全命中，1 条字面漂移

1. **冻结1（全局缓存+映射+公共库=系统空间）**：`entities.py:132` `uq_asset_source_external`（source_id,external_id 唯一）；`:169` `uq_doc_asset_space`（asset_id,space_id 映射）；探针 `p1_public_20260913.txt:11` 公共库 `owner_type=system,is_public=t`。**命中**
2. **冻结2（A拷贝式，link仅预留）**：`ab1004p1a` 迁移 `source VARCHAR(16) DEFAULT 'copy'`（`:49-52`）；`citations.spaceName` 标注在 API 文档 v0.5 ③。**命中**
3. **冻结3（ContentAsset真源+5槽位+Key只走env）**：`adr0004_p0_p4_20260913.txt` 6 用例含 `make_engine(notion) 拒绝`；`config.py:45-76` 各 key 占位空串，全库无明文第三方 Key。**命中**
4. **冻结4（F1/F2/F3 三入口）**：API 文档 v0.4b(单篇)/v0.5b(整号)/v0.5(公共库) 端点齐全；`subscriptions.py:10` 30005；`run-summary.txt` 全链路探针（202→READY→SSE 帧级因 SSO 会话 BLOCKED，DB 直查口径）。**命中**（帧级真实验证有 BLOCKED 登记）
5. **冻结5（迁移冻结）**：5 字段全部落地，但 **「1 个 Alembic 版本」字面漂移**——实际 `ab1004p0a`（hit_count）+ `ab1004p1a`（其余4列）两个版本；回滚策略已登记数据库文档 §六/§七。**部分命中（字面漂移，功能等价）**
6. **冻结6（错误码）**：`errors.py:28` `30005: JOB_STATE_INVALID`；`state_machine.py` 状态机含 PARTIAL_SUCCESS。**命中**
7. **冻结7（串行顺序）**：git log 可见 P0→P1→P2→P4→P5(UX)→修复闭环(T-023) 严格串行；SaaS 三家（Coze/Dify/FastGPT）因 Key 未到位逐个 BLOCKED 登记。**命中**
8. **冻结8（机器门+端口+证据）**：见需求①/④。**命中**

## 三、缺陷闭环（需求③）——P0 全闭环，REWORK 上限未突破

1. **P0 级**：D-04/L-01（短链二次抓取非0请求）修复确认——`test_d04_short_link.py` 3 passed；L-08（公共库文案）修复确认——vitest 75 passed + `grep:app/chat/page.tsx:需先「一键引入」` 命中。**P0 全闭环**
2. **BLOCKED 有依据**：D-05/L-06（worker 执行循环，M3 范围）、L-04（redfox Key 未配 env）、L-09/D-01（onboarding 端点需规格冻结）、D-03（SSO 会话无 code）——均如实登记，不冒充修复。
3. **REWORK 上限**：regression-AB-P004.md:33「本批次 0 次突破（无 REWORK/ESCALATED 登记）」；git log 亦无 REWORK/ESCALATED 提交标记。
4. **遗留登记**：L-02（批量粘贴，P1 遗留，仅「超出串行窗口」范围依据）、L-05（断网进度，P2 遗留）。P1 级 L-02 未闭是未能 PASS 的主因之一。

## 四、端口/密钥/证据台账（需求④）——全部合规

1. **端口铁律 3333 唯一**：`netstat -ano` 仅 3333 有 LISTEN（0.0.0.0:3333=PID 27388 com.docker.backend；[::1]:3333=PID 35664 wslrelay——同一 Docker 前端容器经 WSL 转发，非双前端实例）；**无 3334/3335 LISTEN**。
2. **代码 grep 无 3334/3335**：仅命中 `.venv/Lib/site-packages/` 第三方依赖（idna/pip/rich），项目源码零命中。
3. **密钥纪律**：`grep` 全库无 `sk-`/`AIza`/长串明文 Key；`config.py:45-76` 各第三方 key 均占位空串，只走 env/.env。注：`文档索引.md:45` 存在 SSO 开发密钥 `wechat-rag-dev-secret-please-rotate`，属主平台 SSO dev secret 类别（非本批第三方 API Key），为历史既有文案，非 AB-P004 新增明文。
4. **证据台账**：`p0/p1/p2/adr0004` 四份证据文件在 `/e/Code/AideanBot/.workbuddy/evidence/`，账实相符。

## 五、文档同步（需求⑤）——实质一致，存在 3 处同步缺口（P2 类）

1. **API接口文档**：v0.4b/v0.5/v0.5b/v0.5c 变更条齐全，与实际端点（spaces/public、links、sources/subscriptions/jobs、engines、citations 三元）逐条对应。但**头部版本号仍为 v0.1（L3），未随 v0.5c 更新**——轻微漂移。
2. **数据库文档**：§六（ab1004p0a hit_count 回滚 `alembic downgrade -1` 删列）、§七（ab1004p1a 5 列回滚）与迁移文件 `ab1004p0a_p0_asset_hit_count.py`/`ab1004p1a_p1_public_library.py` 一致，回滚策略已登记。**一致**
3. **文档索引**：§四「待建文档」仍列 `API 接口文档（AideanBot 自身 v1 契约）` 为待建，而该文件已存在（14732 字节，2026-09-14 更新）；§二核心文档表亦未收录 API接口文档。**同步缺口（P2）**
4. **ADR-0004 §八 实现状态**：登记 P0 端口抽取/P1 字段/P4 端点状态，与实际实现一致。**一致**

---

## 六、缺陷登记（只登记不修改）

- 建议-1（文档同步，P2）：`文档索引.md` §四 将已存在的 API接口文档.md 标为「待建」、§二 未收录——责任位置 `.docs/文档索引.md`，建议纳入下次文档收口。
- 建议-2（文档同步，P2）：`API接口文档.md` L3 头部版本号 v0.1 未随 v0.5c 刷新——责任位置 `.docs/API接口文档.md:3`。
- 建议-3（冻结口径字面，P2）：冻结5「1 个 Alembic 版本」与实际 `ab1004p0a`+`ab1004p1a` 两版本不符（功能等价、回滚已登记）——责任位置 `freeze-scope-AB-P004.md` 冻结5，建议口径澄清或登记变更。
- 建议-4（P1 遗留，已登记）：L-02 批量粘贴未闭，仅「超出串行窗口」范围依据，无硬外部 BLOCKED——责任位置 `fix-log-frontend.md` F-02，需下轮明确受理或降级为「明确不做」。

## 七、审查结论

P0 缺陷全闭环、机器门独立复核全绿、端口/密钥/证据台账合规、冻结 8 条实质命中（1 条字面漂移功能等价）、REWORK 上限未突破。存在 P1 遗留（L-02）与多处 P2 类同步/口径缺口（文档索引、API 头部版本、冻结字面）均已有登记。综合四态：**PARTIAL**。
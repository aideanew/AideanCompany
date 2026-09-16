# PRD PM-001 · xiaohongshu_create（CTXHS）「五、未完成事项」4 项修复

> 任务编号：PM-001 | 产出：pm-1 | 日期：2026-09-14
> 目标文件：`E:/Code/AideanCompany/fleet/projects/xiaohongshu_create-fix-goal.txt`（3776 字节，26 行全文已读取，未截断）
> 上游证据：`E:/Code/AideanCompany/fleet/reports/xiaohongshu_create-20260914.md` §五（未完成事项 1–5）、§7（worker-c 配置漂移注）
> 代码基线：`E:/Code/NPX/xiaohongshu_create`，HEAD `7eb3514` + 未提交工作区（Settings 基线 467 pass / 0 fail 已验收）

---

## 1. 需求目标

完成收尾报告「五、未完成事项」中的 4 项修复（第 5 项真实 POST 201 验证继续冻结）：

| 编号 | 目标 | 对应目标文件工作包 | 对应上游未完成事项 |
|---|---|---|---|
| G1 | `evaluateWorkflowReadiness` 接入 `POST /api/tasks` 创建门禁（consumeUse 之前判定，失败不扣额度，HTTP 400 `WORKFLOW_NOT_READY`）+ `GET /api/models` 新增 `workflowReadiness[]` 视图（不破坏既有 `readiness[]` 契约） | W1(A)(B) | 事项 1 |
| G2 | 同步 `CTXHS_文档索引.md` 与 `CTXHS_验证清单.md`：R3 违规检测半边状态改为已完成 | W1(D) | 事项 1 收尾 |
| G3 | `workflows/image-text.yaml` 与 `workflows/prompt-only.yaml` 各增 1 个 `collect` Step（`skill: collect`，入参含 `dataSource` 与 `credentialRef`，从任务 input 透传；`dataSource=none` 时跳过，参照 duplicate-check 的 when 写法） | W2(E) | 事项 2 |
| G4 | `packages/runtime-native/src/sample-skills.ts` 新增 `collect` 确定性执行器（`artifactType: CollectReport`，输出 `{dataSource, skipped, materials[]}`，`dataSource=none` 返回 `skipped: true`），确保 runtime-native 全链路可跑 | W2(F) | 事项 2 |
| G5 | 测试与验收：collect when 跳过语义、W1 门禁三态、全链路 `npm test/typecheck/build/lint/git diff --check` 全绿、禁改项零改动 | W3(G) | 事项 1+2 收口 |

注：上游未完成事项 3（Settings 前端交互回归）与 4（Manager a2a 复验）不在本 4 项范围（目标文件明文圈定 W1/W2/W3），见 §3.2。

## 2. 需求范围

### 2.1 做什么（In Scope，与目标文件允许改动范围一致）

**W1（后端门禁，be-2；允许改：`apps/web/src/server/app.ts`、`apps/web/src/server/model-readiness.ts`（如需）、`apps/web/test/` 新增或 phase4.test.ts、`CTXHS_文档索引.md`、`CTXHS_验证清单.md`）**
- (A) `createTask` 门禁：创建任务时按所选 workflow 加载并调 `evaluateWorkflowReadiness`，`satisfied === false` 拒绝创建（HTTP 400，错误码 `WORKFLOW_NOT_READY`，信息含 `workflowId` 与 `issues` 摘要）；**判定必须位于 `services.licenses.consumeUse()`（`app.ts:659` 原文 `await services.licenses.consumeUse();`）之前**，校验失败不扣额度。
- (B) `GET /api/models`（`app.ts:845` 原文 `readiness: readinessByProfile(services)`）响应为每个已加载 workflow 附 `workflowReadiness[]`（`WorkflowReadinessView`：workflowId / referencesViolationCheck / satisfied / issues），不破坏既有 `readiness[]` 契约（phase4 9 例依赖）。
- (C) 测试四态：拒绝不扣额度（断言 `used_count` 不变）/ satisfied 放行 / 无 violation-check 的 workflow 不受影响（`model-readiness.ts:154` 既有 `satisfied: true` 短路）/ readiness 视图新增字段。
- (D) 文档同步：两份 CTXHS 文档 R3 半边状态改为已完成（以 AC1–AC4 实测通过为前提，见 §5 决策 D1）。

**W2（工作流+运行时，be-3；允许改：`workflows/*.yaml`、`packages/runtime-native/src/sample-skills.ts`、`packages/runtime-native/test/*`、`packages/workflow/test/*`）**
- (E) 两个 YAML 各增 `collect` Step（`id: collect`，`skill: collect`），入参 `dataSource` / `credentialRef` 从任务 input 透传（`$ref: input.dataSource` / `$ref: input.credentialRef`）；`dataSource=none` 跳过语义参照 `image-text.yaml:28-30` duplicate-check 的 `when: $bool: input.duplicateCheck` 写法。
  - DSL 现状证据（`packages/workflow/src/schema.ts:21-27` 原文）：`WhenExpressionSchema = z.union([$bool, $equals, $always])`，**无取反/否定形式**——「none 时跳过」无法直接用 when 正向表达；按目标文件授权（"若 DSL 需取反可据实处理"），首选兜底方案：collect 执行器内短路返回 `skipped: true`，YAML 侧 when 仅作语义标记（见 §5 决策 D2）。若 topic-generation 已用 benchmarkAccounts 做采集语义，collect 与其互补而非重复，由 be-3 按工作流语义判断落位。
- (F) `sample-skills.ts` 新增 collect 确定性执行器：`artifactType: "CollectReport"`，输出 `{dataSource, skipped, materials[]}`；无真实采集，`dataSource=none` 返回 `skipped: true`。现状证据：`grep -n "CollectReport\|collect" packages/runtime-native/src/sample-skills.ts` 退出码 1（0 命中，确认待新增）。

**W3（测试+验收，worker-c 优先，烟测失败则 be-3 兼任；允许改：`apps/web/test/*`、`packages/runtime-native/test/*`、`packages/workflow/test/*`）**
- (G) 覆盖：collect when 跳过语义（DSL 解析+校验+运行时 skipped）；W1 门禁三态；全链路 `npm test / typecheck / build / lint / git diff --check` 全绿；禁改项（`packages/storage/src/schema.ts` 既有表、license 子系统、`apps/electron`）零改动。

### 2.2 明确不做什么（Out of Scope）

1. 第 5 项真实 `POST /api/tasks` 201 全链路验证——继续冻结，禁止对 1994 活体发真实 POST（额度冻结铁律，目标文件明文）。
2. 禁止 `git commit` / `git push`（只改工作区文件，由管理者统一提交）。
3. 禁止改 license 子系统与 `apps/electron`；禁止改 `packages/storage/src/schema.ts` 既有表。
4. 禁止任何 API Key 明文进代码/测试/报告。
5. 不实现真实数据采集（collect 仅确定性示例执行器，真实采集接线属后续需求）。
6. 不改动已验收的 `GET/PUT /api/settings` 契约与 fe-2 已交付 Settings 前端（`settings.tsx` 等），仅在 467 pass 基线上做增量。
7. 上游未完成事项 3（Settings 前端交互回归测试）、4（Manager a2a 复验）不在本 4 项范围。
8. `WorkflowReadinessView` 覆盖面不扩大：门禁判定仅限 violation-check 引用关系（既有纯函数语义），不引入新 role 检查。

## 3. 验收标准（可机器执行）

| # | 验收项 | 验收方式（可执行命令/断言） | 通过判定 |
|---|---|---|---|
| AC1 | 门禁拒绝且不扣额度 | `npx tsx --test apps/web/test/<门禁测试>`：构造引用 violation-check 且对话绑定缺失/ghost 的 workflow → `POST /api/tasks` | 400，`code=WORKFLOW_NOT_READY`，`details` 含 `workflowId` 与 `issues` 摘要；license `used_count` 断言不变 |
| AC2 | 门禁放行 | 同 workflow + 完整对话绑定 → `POST /api/tasks` | 请求通过 workflow 门禁，进入既有模型就绪判定与后续流程 |
| AC3 | 无 violation-check 的 workflow 不受影响 | 用不含 violation-check 的 YAML 发 `POST /api/tasks` | 行为与改前一致，无 `WORKFLOW_NOT_READY`（`model-readiness.ts:154` 短路） |
| AC4 | `GET /api/models` 新字段 | 测试或 curl 请求该端点 | 响应含 `workflowReadiness[]`（每元素含 workflowId/referencesViolationCheck/satisfied/issues）；既有 `readiness[]` 逐字段不变（phase4.test.ts 全绿） |
| AC5 | collect 跳过语义 | `packages/workflow/test/*` 新用例 + runtime-native 端到端：`input.dataSource=none` 运行 `image-text` | YAML 经 schema 校验通过；collect 输出 `skipped: true`、`materials: []`；`dataSource!=none` 时输出示例 `materials` |
| AC6 | 文档同步 | `grep -n "R3" CTXHS_文档索引.md CTXHS_验证清单.md` | R3 违规检测半边状态表述为已完成，无「受阻」字样残留（以 AC1–AC4 通过为前提） |
| AC7 | 全链路全绿 | `cd E:/Code/NPX/xiaohongshu_create && npm test && npm run typecheck && npm run build && npm run lint && git diff --check` | 全部 exit 0；测试 ≥ 467 pass / 0 fail（含新增增量） |
| AC8 | 禁改审计 | `git diff --name-only -- packages/storage/src/schema.ts packages/storage/src/licenses.ts && git status --porcelain apps/electron` | 输出为空 |
| AC9 | 额度冻结合规 | 审计本批次对 1994 活体的真实 `POST /api/tasks` 请求数 | 0 次 |
| AC10 | 执行器完备 | `npm run -w @ctxhs/runtime-native test`（runtime-native 全链路） | `image-text` / `prompt-only` 全部被引用 skill 均有执行器，链路跑完 |

## 4. 页面/接口清单（增量）

| 类型 | 名称 | 变更 |
|---|---|---|
| 接口 | `POST /api/tasks` | 新增 workflow 级门禁：`satisfied===false` → 400 `WORKFLOW_NOT_READY`（details 含 workflowId + issues 摘要）；插入点在 `consumeUse` 之前 |
| 接口 | `GET /api/models` | 响应新增 `workflowReadiness[]`（每 workflow 一个 `WorkflowReadinessView`）；既有 `readiness[]` 不变 |
| 工作流 | `workflows/image-text.yaml`、`workflows/prompt-only.yaml` | 各 +1 Step（collect，入参 dataSource/credentialRef，none 跳过） |
| 技能 | `collect`（sample-skills.ts 新执行器） | `CollectReport`：`{dataSource, skipped, materials[]}` |
| 文档 | `CTXHS_文档索引.md`、`CTXHS_验证清单.md` | R3 违规检测半边状态改为已完成 |
| 前端 | 无 | 本轮不改前端页面 |

## 5. 任务拆解建议（含依赖与并行）

| 包 | 内容 | 建议执行者 | 依赖 | 并行性 |
|---|---|---|---|---|
| W1 (A)(B)(C)(D) | `app.ts` 门禁 + `GET /api/models` 视图 + 四态测试 + 两份 CTXHS 文档同步 | be-2（已熟 `app.ts`，上轮交付 GET/PUT /api/settings） | 无（`evaluateWorkflowReadiness` 已存在于 `model-readiness.ts:143`） | 与 W2 并行（文件不相交） |
| W2 (E)(F) | 两个 YAML collect Step + `sample-skills.ts` 执行器 + 相关测试 | be-3（上轮交付 B 包，熟 workflow/runtime 侧） | 无 | 与 W1 并行 |
| W3 (G) | collect 跳过语义 + 门禁三态 + 全链路全绿 + 禁改审计 | worker-c 优先；派工前烟测（网关探活 + 短指令回执），若仍 `Provider authentication failed` 则 be-3 兼任并在报告注明 | W1 + W2 回执后串行 | 串行 |
| 收口 | 管理者亲自跑 §3 验收命令判 PASS/PARTIAL/REWORK/BLOCKED；REWORK ≤ 3；六节报告 + 完成度表落盘 `E:\Code\AideanCompany\fleet\reports\xiaohongshu_create-fix-20260914.md` | 管理者 | W3 全绿 | — |

**决策点（目标文件未完全指定处，供管理者/执行者裁决）**

| 编号 | 决策点 | 建议 | 依据 |
|---|---|---|---|
| D1 | 文档同步 (D) 是否等 W3 全绿后才改 | 是：R3 改「已完成」以 AC1–AC4 实测通过为前提，避免文档先于证据 | 全员铁律 3（证据优先） |
| D2 | `dataSource=none` 跳过语义落地方式 | 首选：collect 执行器内短路 `skipped: true` + YAML when 作语义标记；不动 `packages/workflow/src` 的 WhenExpressionSchema（改动会扩大 W3 禁改审计面）；目标文件已授权「需取反可据实处理」，若 be-3 判定必须改 DSL 则单独上报管理者 | `schema.ts:21-27` union 仅 `$bool/$equals/$always`，无否定形式 |
| D3 | collect Step 位置 | 由 be-3 按工作流语义判断（与 benchmarkAccounts/topic-generation 互补而非重复）；原则上素材采集先于选题，若下游 `$ref` 依赖 topic 输出则置后，YAML 内不引入循环依赖 | 目标文件明文「按你对工作流语义的判断落位」 |
| D4 | `WORKFLOW_NOT_READY` details 结构 | 对齐既有 `VALIDATION_FAILED` 风格（`app.ts:626-640` 既有模式：workflowId + issues[] 摘要），保持客户端可解析 | 既有代码模式 |
| D5 | worker-c 认证问题 | 本轮按目标文件执行烟测+兼任预案；上轮 §7 注已定位疑因（profile base_url 已切 BAI 而 `api_key` 变量仍指 ModelScope，Key/base_url 错配）——**修复属管理者/人工配置项，不在本任务包范围**，建议另行提交管理者核对 Key 后重启 worker-c 网关 | fleet 报告 §7 注 |

## 6. 风险

| 风险 | 等级 | 缓解 |
|---|---|---|
| worker-c 网关 `Provider authentication failed`（上轮已复现，疑 Key/base_url 错配） | 高 | 派工前烟测；be-3 兼任预案写入任务包；Key 修复另行提交管理者 |
| 在 `consumeUse` 前插入门禁时误改既有 `licenseAuth` 中间件优先级 | 中 | AC1 显式断言 `used_count` 不变；AC8 禁改审计含 license 子系统 |
| 额度冻结：本批次任何对 1994 的真实 POST 都消耗一次性卡额度 | 高 | AC9 审计 0 次真实 POST；禁止 git push/commit 保持工作区可回退 |
| `workflows/*.yaml` 被 electron 打包 extraResources 拷贝，YAML 改动需重新 build 才进安装包 | 低 | 验收以开发态 `npm test` 为准；重打包不在本包（`apps/electron` 禁改） |
| fe-2 浏览器级渲染无 jsdom（上轮遗留，不在本 4 项） | 中 | W3 全量 `npm test` 含 settings-contract 30 例回归即可兜底 |

## 7. 证据链（文件读取/命令输出证据）

| 证据 | 来源 | 摘录/结果 |
|---|---|---|
| 目标文件全文可读 | `E:/Code/AideanCompany/fleet/projects/xiaohongshu_create-fix-goal.txt` | 26 行 / 3776 字节完整读取（退出码 0），含 W1–W3、铁律、Full Auto 指令 |
| 4 项未完成事项 | `E:/Code/AideanCompany/fleet/reports/xiaohongshu_create-20260914.md` §五（第 87–93 行） | 「1. evaluateWorkflowReadiness 尚未接入 app.ts…；2. 仍无 collect Step 与 dataSource=none 的 when 跳过逻辑；5. 真实 POST 201 未做（铁律禁止）」 |
| 门禁插入点 | `apps/web/src/server/app.ts:653-659` | 原文注释 `Quota is spent only after the request proved valid…` + `await services.licenses.consumeUse();` |
| `evaluateWorkflowReadiness` 已存在 | `apps/web/src/server/model-readiness.ts:143` | `export function evaluateWorkflowReadiness(…): WorkflowReadinessView`；`154 行 satisfied: true`（无 violation-check 短路）、`172 行 satisfied: issues.length === 0` |
| `GET /api/models` 现状 | `apps/web/src/server/app.ts:845` | `readiness: readinessByProfile(services)` |
| 错误码表既有模式 | `apps/web/src/server/app.ts:121` | `VALIDATION_FAILED: 400`；`app.ts:626-640` details 结构（workflowId/roles/issues） |
| WhenExpressionSchema 现状 | `packages/workflow/src/schema.ts:21-27` | union 仅 `$bool` / `$equals` / `$always`，无否定形式（决策 D2 依据） |
| duplicate-check when 参考写法 | `workflows/image-text.yaml:28-30` | `skill: duplicate-check` + `when:\n  $bool: input.duplicateCheck`；violation-check 位于 `109 行`（caption-writing `94 行` 之后） |
| collect 执行器待新增 | `grep -n "CollectReport\|collect" packages/runtime-native/src/sample-skills.ts` | 退出码 1（0 命中） |
| 两个 YAML skill 清单 | `grep -n "skill:" workflows/*.yaml` | image-text 8 个 skill（topic-generation…final-qa，无 collect）；prompt-only 7 个 skill（无 collect） |
| 工作区基线 | `git log --oneline -1` | `7eb3514 feat(phase3): Step14-20 + Step21-28 收口…`，与目标文件声明一致 |
| worker-c 认证风险 | fleet 报告 §7 注 | base_url=BAI 而 `api_key` 仍指 `HERMES_CUSTOM_API_MODELSCOPE_API_KEY`，错配疑为根因 |

## 8. 交付说明

- 本 PRD 为需求分析产物，未改动任何项目源代码/配置/依赖；唯一新增文件为本文件。
- 建议管理者按 §5 拆解直接派工：W1/W2 并行、W3 串行（worker-c 烟测失败即 be-3 兼任）、收口判四态，REWORK ≤ 3。
- 完整展开版（含逐条 AC 细化与既有同题分析）见 `E:/Code/AideanCompany/fleet/reports/xiaohongshu_create_prd.md`（上一轮产出，与本 PRD 结论一致；本 PRD 为准，两处差异已在本 PRD 更正：WhenExpressionSchema 实为 `$bool/$equals/$always` 三元 union，既有 PRD §9 仅记两元）。

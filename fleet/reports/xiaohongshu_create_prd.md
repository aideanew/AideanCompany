# PRD：xiaohongshu_create（CTXHS）收尾修复 4 项 —— 需求分析报告

> 任务编号：XHS-REQ-001 | 分析人：pm-1 | 日期：2026-09-14
> 需求来源：`E:/Code/AideanCompany/fleet/projects/xiaohongshu_create-fix-goal.txt`（21 行全文已读取，证据见 §9）
> 佐证来源：`E:/Code/AideanCompany/fleet/reports/xiaohongshu_create-20260914.md`（收尾报告「五、未完成事项」、§7 配置漂移注）、
> 代码库 `E:/Code/NPX/xiaohongshu_create`（HEAD `7eb3514` + 未提交工作区，Settings 467 pass / 0 fail 已验收）

---

## 1. 需求目标

完成上一轮收尾报告「五、未完成事项」中的 4 项修复，并同步文档状态；第 5 项（真实 POST 201 全链路验证）**继续冻结、禁止执行**（额度冻结铁律）。

| 编号 | 目标 | 来源（未完成事项 → 工作包） |
|---|---|---|
| G1 | 将 `evaluateWorkflowReadiness` 接入 `POST /api/tasks` 创建门禁 + `GET /api/models` 增加 `workflowReadiness[]` 视图 | 未完成事项 1 → W1(A) |
| G2 | 同步 `CTXHS_文档索引.md` 与 `CTXHS_验证清单.md`：R3 受阻状态改为「已完成（violation-check 双半边全闭环）」 | 目标文件 W1(B) |
| G3 | 为 `image-text.yaml` 与 `prompt-only.yaml` 增加 `collect` Step，支持 `dataSource=none` 时跳过 | 未完成事项 2 → W2(C) |
| G4 | `sample-skills.ts` 新增 `collect` 确定性执行器（所有被引用技能必须有执行器，runtime-native 全链路可跑） | 目标文件 W2(D) |
| G5 | 测试与验收：collect 跳过语义、门禁三态、全链路全绿、禁改项零改动 | 目标文件 W3(E) |

## 2. 需求范围

### 2.1 做什么（In Scope）

**W1（后端门禁，be-2，允许改 `apps/web/src/server/app.ts` + 新增测试）**
- (A1) `createTask` 中在 `evaluateModelReadiness`（`app.ts:622`）之后、`services.licenses.consumeUse()`（`app.ts:659`）**之前**追加 workflow 级门禁：按所选 workflow 加载的 `WorkflowDefinition` 调 `evaluateWorkflowReadiness`，`satisfied === false` 时拒绝创建。
  - 错误契约（建议值）：`code: "WORKFLOW_NOT_READY"`，HTTP 400，`details` 含 `workflowId` 与 `issues` 摘要（沿用 `ModelReadinessIssue` 结构：role/message/severity）。
  - 顺序铁律：校验失败**不扣额度**（`consumeUse` 只在放行后执行）——这是目标文件明文要求，也是 `app.ts:653` 注释既有的额度语义。
  - 三态（验收 G5(E)）：不满足→拒绝且不扣额度；satisfied→放行；workflow 无 violation-check→`satisfied: true`（`model-readiness.ts:155` 既有短路逻辑）不受影响。
- (A2) `GET /api/models`（`app.ts:845` 的 `readinessByProfile`）响应里**新增** `workflowReadiness[]` 字段：对每个已加载 workflow 附 `evaluateWorkflowReadiness` 视图（`WorkflowReadinessView`：workflowId / referencesViolationCheck / satisfied / issues）。
  - 契约边界：**不得破坏既有 `readiness[]` 结构**（phase4.test.ts 9 例依赖 `.readiness[]`）。
- (B) 文档同步：`CTXHS_文档索引.md` R3 行 / `CTXHS_验证清单.md`「三、受阻项」R3 改为已完成，注明 violation-check 双半边全闭环（对话半边 + 违规半边经门禁闭环）。

**W2（工作流 + 运行时，be-3，允许改 `workflows/*.yaml` + `packages/runtime-native/src/sample-skills.ts` + 相关测试）**
- (C) 两个 YAML 各增 1 个 Step：`id: collect`，`skill: collect`；位置由 be-3 按判断放 topic-generation 之前或之后（本报告建议**之前**：素材采集逻辑上先于选题）；入参含 `dataSource` 与 `credentialRef`（从任务 input 透传，`$ref: input.dataSource` / `$ref: input.credentialRef`）。
  - 跳过语义：`dataSource=none` 时跳过。实现路径（目标文件已给两条，取其一或组合）：
    1. 首选 DSL：`when: $equals {path: input.dataSource, value: "none"}` 的**取反**语义。⚠️ 经核查 `packages/workflow/src/schema.ts:22-24`，`WhenSchema` 仅支持 `$bool`（路径布尔值）与 `$equals`（相等）**两种且为正向匹配，DSL 不支持取反/否定**；`expressions.ts:179-183` 亦无 `!$equals`。因此「none 时跳过」无法直接用现有 when 表达——见 §6 决策点 D1。
    2. 兜底（目标文件允许）：`collect` 执行器内直接短路返回 `skipped: true`，workflow YAML 用 `$equals` 控制下游依赖。
  - 参考写法：`image-text.yaml` 的 duplicate-check `when: $bool: input.duplicateCheck`（第 30 行）。
- (D) `sample-skills.ts` 新增 collect 确定性执行器：`artifactType: "CollectReport"`；输出 `{dataSource, skipped, materials[]}`；无真实采集实现，按 `input.dataSource` 返回示例素材或 `skipped`。约束：「所有工作流引用的技能必须有执行器」——`image-text`/`prompt-only` 中其余 skill 已有 sample 执行器（TopicCandidates/ResearchReport/ImagePlan 等已确认存在），新增后全链路 `runtime-native` 可跑。

**W3（测试 + 验收，worker-c 或 be-3 兼任，允许改 `apps/web/test/*`、`packages/runtime-native/test/*`、`packages/workflow/test/*`）**
- (E) 新增/扩展测试：
  - collect Step 的 when 跳过语义（DSL 解析 + 校验，`packages/workflow/test/*`）；
  - W1 门禁三态（`apps/web/test/*`，建议新增于 `workflow-readiness.test.ts` 或 phase4 扩展）：不满足→400 `WORKFLOW_NOT_READY` 且不扣额度（断言 `used_count` 不变）；satisfied→放行；无 violation-check 的 workflow 不受影响；
  - 全链路验收：`npm test` / `npm run typecheck` / `npm run build` / `npm run lint` / `git diff --check` 全绿（基线 467 pass / 0 fail 之上增量）；
  - 禁改项零改动审计：`packages/storage/src/schema.ts` 既有表、license 子系统、`apps/electron`。

### 2.2 明确不做什么（Out of Scope）

1. **第 5 项真实 `POST /api/tasks` 201 全链路验证**：继续冻结，禁止对 1994 活体发真实 POST（额度冻结）；门禁正确性以测试内断言代替。
2. 禁止 `git commit` / `git push`。
3. 禁止改 license 子系统与 `apps/electron`。
4. 禁止任何 API Key 明文出现在代码/配置/报告中。
5. 不实现真实数据采集（collect 仅为确定性示例执行器，真实采集接线属后续需求）。
6. 不改动 `GET/PUT /api/settings` 既有契约（Settings 467 pass 已验收基线之上只做增量）。
7. 不扩大 `WorkflowReadinessView` 覆盖面：门禁判定仅限 violation-check 引用关系（既有纯函数语义），不引入新 role 检查。
8. 不动 fe-2 已交付的 Settings 前端（`settings.tsx`/`settings-body.ts`/`settings-contract.test.ts`）。

## 3. 验收标准（可机器执行）

| # | 验收项 | 验收方式（可执行） | 通过判定 |
|---|---|---|---|
| AC1 | 门禁拒绝 | 测试内构造 workflow 引用 violation-check 且对话绑定缺失/ghost → `POST /api/tasks` | 400，`code=WORKFLOW_NOT_READY`，`details.workflowId` 正确，`details.issues` 非空；**且 license `used_count` 不变**（不扣额度） |
| AC2 | 门禁放行 | 同一 workflow + 完整对话绑定 | 请求通过 workflow 门禁（进入既有模型就绪判定与后续流程） |
| AC3 | 无 violation-check 的 workflow 不受影响 | 用不含 violation-check 的 YAML 发 `POST /api/tasks` | 行为与改前一致，无 `WORKFLOW_NOT_READY` |
| AC4 | `GET /api/models` 新字段 | 启动 web 服务后请求该端点（测试或 curl） | 响应含 `workflowReadiness[]`，每元素含 workflowId/referencesViolationCheck/satisfied/issues；**既有 `readiness[]` 逐字段不变** |
| AC5 | collect 跳过语义 | `packages/workflow/test/*` 新用例 + runtime-native 端到端：`input.dataSource=none` | collect 输出 `skipped: true`、`materials: []`；`dataSource!=none` 时输出示例 `materials`；YAML 经 schema 校验通过 |
| AC6 | 文档同步 | `grep` `CTXHS_文档索引.md` / `CTXHS_验证清单.md` 中 R3 行 | R3 状态表述为已完成（双半边闭环），无「受阻」字样残留 |
| AC7 | 全链路全绿 | `cd E:/Code/NPX/xiaohongshu_create && npm test && npm run typecheck && npm run build && npm run lint && git diff --check` | 全部 exit 0，测试 ≥ 467 pass / 0 fail（含新增） |
| AC8 | 禁改审计 | `git diff --name-only -- packages/storage/src/schema.ts` 及 license 子系统文件、`git status --porcelain apps/electron` | 输出为空 |
| AC9 | 额度冻结合规 | 审计本批次无任何对 1994 活体的真实 `POST /api/tasks` | 0 次真实请求 |
| AC10 | 执行器完备 | `runtime-native` 全链路测试 | `image-text` / `prompt-only` 两个 workflow 所有被引用 skill 均有执行器，链路可跑完 |

## 4. 页面/接口清单（增量）

| 类型 | 名称 | 变更 |
|---|---|---|
| 接口 | `POST /api/tasks` | 响应错误码新增 `WORKFLOW_NOT_READY`（400）；行为：workflow 级门禁插入在 consumeUse 之前 |
| 接口 | `GET /api/models` | 响应新增 `workflowReadiness[]`（每 workflow 一个 `WorkflowReadinessView`）；`readiness[]` 不变 |
| 数据 | `app_settings`（既有） | 读取 `dataSource` / `credentialRef` 透传给 collect Step（W2 依赖 Settings 后端已就绪） |
| 工作流 | `workflows/image-text.yaml`、`prompt-only.yaml` | 各 +1 Step（collect） |
| 技能 | `collect`（sample-skills.ts 新执行器） | `CollectReport`：`{dataSource, skipped, materials[]}` |
| 文档 | `CTXHS_文档索引.md`、`CTXHS_验证清单.md` | R3 状态更新 |
| 前端 | 无 | 本轮不改前端页面（Settings 表单已有） |

## 5. 任务拆解建议（含依赖与并行）

| 包 | 内容 | 建议执行者 | 依赖 | 可并行 |
|---|---|---|---|---|
| W1(A1+A2) | app.ts 门禁 + GET /api/models 视图 + 测试 | be-2（最熟 app.ts，其已写 GET/PUT /api/settings） | 无（纯函数 `evaluateWorkflowReadiness` 已存在） | 与 W2 并行（文件不相交） |
| W1(B) | 两份 CTXHS 文档 R3 状态同步 | be-2 同包内顺手完成 | 同 W1(A) | 同上 |
| W2(C+D) | 两个 YAML + collect 执行器 + 测试 | be-3 | 无 | 与 W1 并行（`workflows/*`、`runtime-native/*` 与 W1 文件不相交） |
| W3(E) | 门禁三态 + collect 语义 + 全链路验收 + 禁改审计 | worker-c（先烟测：`a2a_list` 确认在线后发「请只回复两个字：就绪」；若仍 Provider authentication failed 则 **be-3 兼任**并在报告中注明） | W1+W2 回执后串行 | 串行 |
| 收口 | 管理者亲自跑验收命令判四态；REWORK 上限 3 次；六节报告 + 完成度表落盘 `E:\Code\AideanCompany\fleet\reports\xiaohongshu_create-fix-20260914.md` | 管理者 | W3 全绿 | — |

验收建议（每个任务包回执后）：管理者跑 `npx tsx --test <对应测试文件>` + `git diff --name-only` 核对允许改动范围，再全量 `npm test` 一次收口。

## 6. 决策点（需管理者/执行者裁决，目标文件未完全指定处）

| 编号 | 决策点 | 本报告建议 | 依据 |
|---|---|---|---|
| D1 | `dataSource=none` 跳过语义：DSL 不支持取反（`WhenSchema` 仅 `$bool`/`$equals` 正向，`schema.ts:22-24`） | 采用目标文件兜底方案：collect 执行器内短路 `skipped:true`；YAML 侧保留 `when: $equals {path: input.dataSource, value: "none"}` 仅作**下游依赖/文档语义标记**；若 be-3 认为需在 DSL 层表达「非 none 才执行」，则最小改为在 input 侧约定布尔位（如沿用 Settings 侧数据）——**优先不动 `packages/workflow/src` 的 WhenSchema**（该包改动会扩大 W3 禁改审计面） | `expressions.ts:179-183` 实现；改动 schema 会影响全工作流校验 |
| D2 | collect Step 位置（topic-generation 前/后） | 之前：素材采集先于选题符合数据流；若 downstream `$ref` 依赖 topic 输出则其后——以实际引用关系为准，YAML 内不引入循环依赖 | 目标文件「按你判断」 |
| D3 | `WORKFLOW_NOT_READY` 错误 details 结构 | 对齐既有 `VALIDATION_FAILED` 的 details 风格（workflowId + issues[] 摘要），保持客户端可解析 | `app.ts:626-640` 既有模式 |
| D4 | 文档同步 W1(B) 是否需等 W3 全绿后才改 | 是：R3 改「已完成」以门禁实测（AC1-AC4）通过为前提，避免文档先于证据 | 全员铁律 3（证据优先） |
| D5 | worker-c 认证问题（§7 配置漂移注：base_url 已切 BAI 但 `api_key` 仍指 ModelScope） | 本轮按目标文件：先烟测，失败即 be-3 兼任；**Key 错配修复不在本任务包范围内**（属管理者/人工配置项，且「禁止改配置」边界内） | fleet 报告 §7 注 |

## 7. 风险与未完成事项

| 风险 | 等级 | 缓解 |
|---|---|---|
| worker-c 网关 `Provider authentication failed`（Key/base_url 错配，上轮已复现） | 高 | 烟测前置；be-3 兼任预案写进任务包；修复建议另行提交管理者 |
| fe-2 浏览器级渲染未经真实执行（无 jsdom）——上一轮遗留，本轮不涉及但回归时需关注 Settings 表单 | 中 | W3 全量 `npm test` 含 settings-contract 30 例回归即可 |
| 在 consumeUse 前插入门禁时若误改既有 `licenseAuth` 中间件优先级 | 中 | AC1 显式断言 `used_count` 不变；禁改审计含 license 子系统 |
| `workflows/*.yaml` 被 electron 打包 extraResources 拷贝，YAML 改动需重新 build 才生效到安装包 | 低 | 验收以 `npm test`/开发态为准；安装包重打包不在本包 |
| 额度冻结：本批次任何对 1994 的真实 POST 都会消耗一次性卡额度 | 高 | AC9 审计 + 禁止 git push/commit 保持工作区可回退 |

## 8. 后续前后端拆解建议（本 4 项收口之后，不属本轮执行）

1. **后端**：真实数据采集实现替换 collect 示例执行器（按 `dataSource` 枚举分派）；`credentialRef` 的安全解析层（只存引用名的既有约定需补 resolve 端点）。
2. **前端**：Settings 表单增加 `dataSource=none` 时的交互提示与 collect 跳过态可视化；任务详情页展示 `CollectReport` artifact。
3. **测试**：jsdom 渲染回归（fe-2 遗留）；worker-c 网关 Key 修复后重跑 C 包独立验收。
4. **发布**：ADMIN 授权后执行一次真实 `POST /api/tasks` 201 验证（当前冻结的第 5 项）。

## 9. 证据链（文件读取证据）

| 证据 | 来源 | 原文摘录 |
|---|---|---|
| 目标文件全文可读 | `E:/Code/AideanCompany/fleet/projects/xiaohongshu_create-fix-goal.txt` | 21 行 / 3776 字节，`read_file` 完整返回（未截断），含 W1-W3、分工铁律、Full Auto 指令 |
| 4 项未完成事项与 G1-G5 映射 | `E:/Code/AideanCompany/fleet/reports/xiaohongshu_create-20260914.md` §五（第 87-93 行） | 「1. evaluateWorkflowReadiness 尚未接入 app.ts…；2. 仍无 collect Step…；3. Settings 前端交互回归待补；5. 真实 POST 201 未做（铁律禁止）」 |
| consumeUse 位置（门禁插入点） | `apps/web/src/server/app.ts:653-659`（`sed` 输出） | 「Quota is spent only after the request proved valid. … `await services.licenses.consumeUse();`」 |
| evaluateWorkflowReadiness 已存在 | `apps/web/src/server/model-readiness.ts:143` | `export function evaluateWorkflowReadiness(workflow, models): WorkflowReadinessView`；无 violation-check 时 `satisfied: true` 短路（第 155 行） |
| GET /api/models 现状 | `apps/web/src/server/app.ts:845` | `readiness: readinessByProfile(services)` |
| DSL when 无取反 | `packages/workflow/src/schema.ts:22-24`、`expressions.ts:179-183` | `WhenSchema = … $bool … $equals …`，仅两键，无否定形式 |
| duplicate-check when 参考 | `workflows/image-text.yaml:30` | `when:\n  $bool: input.duplicateCheck` |
| sample-skills.ts 既有执行器 | `packages/runtime-native/src/sample-skills.ts` | 已有 TopicCandidates/ResearchReport/ImagePlan/ArticleDraft/QCReport 等 10 个 artifactType；grep `collect` 0 命中（确认待新增） |
| 工作区状态与基线一致 | `git status --porcelain` | 未提交改动清单与 fleet 报告 §二改动文件表一致；HEAD `7eb3514` |
| worker-c 认证风险 | fleet 报告 §7 注 | base_url=BAI 而 api_key 变量仍指 ModelScope，错配疑为 Provider authentication failed 根因 |

## 10. 交付说明

- 本报告为需求分析产物（PRD），未改动任何项目源代码/配置/依赖（合规：仅新增 `E:/Code/AideanCompany/fleet/reports/xiaohongshu_create_prd.md`）。
- 建议管理者将 §5 拆解直接作为任务包分派依据；W1/W2 并行、W3 串行、收口判四态，REWORK ≤ 3。

# CLI 委托分配表（M4 落地，2026-09-14 实测）

> 本文件是“worker 通过本机 CLI 干活”的唯一权威分配。Manager 派工时按此表填写 `delegate_to`；
> worker 收到含 `delegate_to` 的任务包必须走对应 CLI，不得直接手写业务代码，也不得臆测换 CLI。

## 0. 实测结论（本机已验，非推测）

| CLI | 版本 | 登录态 | 非交互命令（已冒烟 `只回复两个字：就绪` → 均回 `就绪`） | 备注 |
|---|---|---|---|---|
| claude | 2.1.270 | OAuth 已登录（firstParty） | `claude -p "<PROMPT>" --output-format text --permission-mode acceptEdits --add-dir E:/Code/AideanBot`（cwd=`E:/Code/AideanBot`） | 质量最高，走订阅，不占 API Key 配额 |
| codex | 0.153.4 | auth.json 有 Key，经本机 15721 代理，模型 `agnes-3.0-flash` | `codex exec --skip-git-repo-check -C E:/Code/AideanBot -s workspace-write "<PROMPT>"` | `-s workspace-write` 是写文件的前提；`read-only` 只能读。`E:/Code/AideanBot` 非 git 仓库，必须带 `--skip-git-repo-check` |
| opencode | 1.18.30 | auth.json 4 凭证（xfyun/atomgit/newapiclaude/Nvidia）；config 有 sensenova/modelscope/nvidia/amd | `opencode run "<PROMPT>" --dir E:/Code/AideanBot -m <provider/model>` | 无交互运行时如遇权限卡点可加 `--auto`（仅限本白名单目录内） |

## 1. 分配矩阵（4 任务包 → 4 执行者 → 3 CLI，reviewer/测试保持原生）

| 任务包 | 执行者 | CLI（子 agent） | 模型 | 分配理由 |
|---|---|---|---|---|
| BE-01 订阅执行引擎端到端闭环（关键路径） | worker-b（后端 A） | claude | OAuth 默认（订阅） | 关键路径配最强代码模型；与 be 系 b.ai 配额隔离，互不挤占 |
| BE-03 SaaS 集成 P3（有前置） | be-2（后端 B，主）/ be-3（备用，同包并行子模块时启用） | codex | agnes-3.0-flash（经 15721 代理，默认即可，不覆写 `-m`） | 与 Manager/pm/reviewer 同模型家族，API 集成风格一致；代理链路已通 |
| FE-01 onboarding 与提问流程 | worker-a（前端 A） | opencode | sensenova/sensenova-6.8-flash-lite | 与 worker-a 原生模型同家族，行为可预期；Key 在 opencode.json 已就绪 |
| FE-02 交易管理页体系 | fe-2（前端 B） | opencode | nvidia/nvidia-nemotron-3-ultra-550b-a55b | 与 FE-01 不同 provider，避免 sensenova 同 Key 并发挤占；NVIDIA Key 在 auth.json 已就绪 |
| 审查（所有包） | reviewer-1 | 不用 CLI（hermes 原生，只审不改） | agnes-3.0-flash | 审查必须独立于执行 CLI，防止自己审自己 |
| 全链路回归（T-024 类） | worker-c | 不用 CLI（hermes 原生，只测不改） | DeepSeek-V4-Flash-0731 | 测试只读验证，用原生即可 |

同一文件/模块禁止两人同时改：BE-01 与 BE-03 按 `backend/app/services/subscription.py vs jobs.py` 拆分；
FE-01 与 FE-02 按 `app/onboarding+chat vs app/spaces+subscriptions` 拆分。be-3 仅在 BE-03 拆出可并行子模块时启用，否则不派工。

## 2. 命令模板（任务包 `delegate_to` 原样填写）

```text
delegate_to:
  worker-b: claude -p "<任务包全文 + 六节报告要求>" --output-format text --permission-mode acceptEdits --add-dir E:/Code/AideanBot
  be-2/be-3: codex exec --skip-git-repo-check -C E:/Code/AideanBot -s workspace-write "<任务包全文 + 六节报告要求>"
  worker-a: opencode run "<任务包全文 + 六节报告要求>" --dir E:/Code/AideanBot -m sensenova/sensenova-6.8-flash-lite
  fe-2: opencode run "<任务包全文 + 六节报告要求>" --dir E:/Code/AideanBot -m nvidia/nvidia-nemotron-3-ultra-550b-a55b
```

cwd 一律 `E:/Code/AideanBot`。PROMPT 必须含完整任务包（目标/允许与禁止/验收命令/证据路径/六节格式/不 commit 不 push/提供商自述/BLOCKED 口径），禁止只发一句话标题。

## 3. 派工前预检（Manager/Launcher 必做，不满足即 BLOCKED，不伪造）

1. `where claude / where codex / where opencode` 均可找到（已验：三者全在 `AppData\Roaming\npm`）。
2. `claude auth status` → loggedIn=true；`127.0.0.1:15721` 可连（codex 代理）；`opencode auth list` 有对应 provider。
3. 目标 worker 的 SOUL 白名单含 `E:/Code/AideanBot`（本次已统一修复）。
4. 证据目录 `E:/Code/AideanBot/.workbuddy/evidence/` 可写。

## 4. 证据链要求（无 transcript 不得判 DONE）

worker 报告除 SOUL 六节外必须追加：
- `CLI：<claude|codex|opencode>，模型：<实际消费 model_id>，命令：<完整命令原文>，cwd，exit 码`；
- CLI 全量输出原文（非摘要）或落盘 transcript 路径（`.workbuddy/evidence/<task>-cli.log`）；
- 验收命令原文输出（ruff/pytest/tsc/vitest/curl/grep），失败原样贴。

## 5. 兜底顺序（CLI 挂了怎么办）

1. 同 CLI 重试 1 次（原样重发，不改任务包）。
2. 仍失败 → 按表内同职能换 CLI 一次：后端 `claude ↔ codex` 互备；前端 `opencode(sensenova) ↔ opencode(nvidia)` 互备。
3. 仍失败 → 回落 hermes 原生执行并在报告注明 `fallback=native`，或标 BLOCKED（外部依赖缺失时）。
4. 429/配额：等 60s→120s 退避 2 次，审计留痕；仍败转 FAILED，不转 DONE。

## 6. 子 agent 口径

hermes 侧 `delegation` 工具集已在通用基座中裁剪，worker 不得再套娃起 hermes 子网关。
本表所称“子 agent”即上述 CLI 进程（每个任务 1 个 CLI 调用为 1 个子 agent，串行；同包多子模块并行时由 Manager 显式拆包后各起 1 个）。

# AideanBot · 舰队协作批次报告（机器门 + 1994 裁决 + 模型重排）

| 项 | 内容 |
|---|---|
| 日期 | 2026-09-13 |
| 执行 | Hermes 七人舰队（Manager=gpt-6-astra）+ ZCode 监督者（机器门与独立校验） |
| 项目 | E:\Code\AideanBot（master，基线快照 stash `023f576d6740`） |
| 整体结论 | **PASS（更新于深夜）**——C-T7 活体终验九步全绿收口（e4cde38），1994 裁决 revert（终裁 3333，e74751b/2e5764c），Key 事故全量回填 8/8 烟测。仅余：ModelScope 余额墙（GLM 启用待充值）、gpt.ge/apifree 两把 FILL_ME（不影响运行） |

## 一、任务清单与状态

| 编号 | 任务 | 执行 | 状态 |
|---|---|---|---|
| T-A | 未提交工作（~1224 行）机器门验证 | ZCode 监督 | ✅ 后端 158 passed/2 skipped + ruff + mypy 46 文件；前端 vitest 63 + build exit 0 |
| T-B | 分域提交（B-T10 批准条件达成） | ZCode 监督 | ✅ 4 提交：de2acd7(backend) / f01c434(frontend) / 7a77e4e(docker) / a96bfa8(docs) |
| T-C | 1994 端口裁决落地（文件层） | ZCode 监督 | ✅ compose 映射/OIDC 默认/playwright 默认/AGENTS 准则/交接文档（36a8785），compose config --quiet 通过 |
| T-D | 1994 运行时切换 | — | ⛔ BLOCKED：1994 被 xiaohongshu_create（PID 34496）占用，按铁律不杀 |
| T-E | C-T7 ① 清理 node_modules.broken-bak | ZCode 监督 | ✅ 已不存在（此前已清） |
| T-F | C-T7 ② 活体终验 ingest→READY→SSE | — | ⛔ BLOCKED：主平台 :3000 未运行（curl 000），SSO 登录链不可达 |
| T-G | mock e2e 回归（playwright 默认端口改动） | ZCode 监督 | ✅ 9/9 passed |
| T-H | 模型重排（按特长） | 基础设施 | ✅ 见 §四 |
| T-I | Key 事故回填（导入骨架覆盖 .env） | ZCode | ✅ 6 组真值回填 + 根因（字面量 `${HTTP_PROXY}`）修复，8/8 烟测 |

## 二、改动文件（本批次）

```text
AideanBot（提交 6 个：de2acd7 → facefd9）
├── docker/compose.yml            1994:3000 映射 + OIDC 回调默认 1994
├── frontend/playwright.config.ts 默认端口 3333→1994
├── AGENTS.md                     端口准则按裁决更新
├── .docs/交接提示词_AI-CLI助手.md 同步
├── .docs/任务进度.md             舰队协作批次记录
└── （此前 4 个分域提交收口 B-T10/C-T7 的 ~1224 行）
```

## 三、验收命令记录（含失败原样）

| 命令 | 结果 |
|---|---|
| backend: `pytest -q` | ✅ 158 passed, 2 skipped, 8.63s |
| backend: `ruff check .` | ✅ All checks passed |
| backend: `mypy app` | ✅ no issues in 46 source files |
| frontend: `pnpm vitest run` | ✅ 63 passed (4 files) |
| frontend: `pnpm build` | ✅ exit 0 |
| frontend: `PORT=3456 NEXT_PUBLIC_API_MOCK=true pnpm test:e2e` | ✅ 9 passed |
| `docker compose config --quiet` | ✅ |
| `curl :1994/` | ⛔ 1994 被 xiaohongshu_create 占用（PID 34496），BLOCKED |
| `curl :3000/` | ⛔ 000，主平台未运行，BLOCKED |
| ModelScope GLM-5.2 / GLM-4.7-Flash 直连 | ⛔ `insufficient balance`（HTTP 429，账户级） |

## 四、返工与修复记录

1. **ModelScope GLM 余额墙**：GLM-5.2/4.7-Flash 均报 insufficient balance → worker-c 按 BAI(优先级=1) 切换 qwen3.8-flash（原 DeepSeek 亦被余额墙波及），GLM-4.7-Flash 挂 fallback 待余额恢复。
2. **reviewer-1/worker-c 切换失败两轮**：profile config 带 BOM + CRLF，正则与状态机两次静默跳过 → 改为 BOM 剥离 + 行级重写 + 回读验证。
3. **网关拒绝启动**：导入事故还原的 `.env` 带 `WEIXIN_GROUP_POLICY=open` → 全部 9 个 .env 改 pairing（否则任何重启全舰队拒启——高危雷已排）。
4. **worker-b 401**：根因同上（`${HTTP_PROXY}` 字面量代理）→ 修复后烟测就绪。

## 五、未完成事项（BLOCKED 详情与解除条件）

| # | 事项 | 解除条件 |
|---|---|---|
| 1 | 1994 运行时切换 | 用户停止 xiaohongshu_create（PID 34496）→ `cd E:\Code\AideanBot\docker && docker compose -p aideanbot up -d --force-recreate frontend` |
| 2 | C-T7 ② 活体终验（ingest→READY→SSE ask，样本 URL 已备：`https://mp.weixin.qq.com/s/tHxEh_qTq8I9PbLkk_qWBw`） | 启动主平台 :3000 + 主平台 OAuth 白名单加 `http://localhost:1994/auth/aidean/callback`（主平台侧授权） |
| 3 | ModelScope GLM 启用 | 账户充值/配额恢复后，worker-c config 的 fallback 已就绪（GLM-4.7-Flash → NVIDIA） |
| 4 | gpt.ge / apifree 两把 Key | 仅在需要切回 gpt-6 以外场景 / Manager 辅助模型时回填（当前均不影响运行） |

## 六、结论

用户指令"完成该任务 + 填补漏洞 + 延申拓展"的可执行部分已全部收口：**B-T10 长期挂起的提交批准以全绿机器门证据落库；1994 端口裁决完成文件层迁移并按纪律记录运行时 BLOCKED；模型按特长重排完毕且烟测全绿**。剩余两项运行时收口均为外部资源 BLOCKED（端口占用 + 主平台离线），解除条件明确、命令就绪，属"能自动化的自动化，不能可靠判定的升级给人"的设计内行为。

## 更正（2026-09-13 终裁）
用户终裁：AideanBot 前端端口维持 3333。1994 迁移已 git revert（e74751b）+ 台账更正（2e5764c）；运行时从未切换（容器一直在 3333 服务，零影响）。C-T7 活体终验剩余前置回到原挂起项：主平台 :3000 启动 + OAuth 白名单含 3333 回调。

## 追加（2026-09-13 深夜）：主平台启动后的收口批次

| 项 | 结果 |
|---|---|
| 主平台 :3000 | 用户启动 ✅（注册/登录 200） |
| SSO 活体链诊断 | 初判"callback 500/400"两轮：第一轮为 09-11 旧证据（B-T10 修复前的 500，修复已随 de2acd7 落容器生效）；第二轮 400/10002 为**探针自身 bug**（用了常量 state 而非后端签发 state）——产品状态机行为完全正确（强校验按设计工作） |
| C-T7 活体终验 | ✅ 九步全绿（注册→登录→SSO→兑换→/me→建空间→活体 ingest 202→5s READY→SSE meta/citations/delta×12，answer_len 86，citations 带真实文章标题）。证据：`.workbuddy/evidence/fleet_ct7_full_chain_20260913.txt` |
| C-T7 收口 | ✅ 后半程三条件闭环（broken-bak 已清/活体终验 PASS/台账 e4cde38），台账标记 C-T7 收口 |
| 发现（非阻塞） | 探针空间 DELETE 返回 405（清理端点方法待 B 下卡核）；ModelScope 账户 insufficient balance（GLM 启用待充值） |

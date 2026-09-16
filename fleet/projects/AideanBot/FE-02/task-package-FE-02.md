# FE-02 · 交易管理页体系（spaces + subscriptions，公共库引入闭环）

> 项目：AideanBot（P-004）｜依赖：P1 公共库契约（GET /spaces/public + POST /links）已在 T-017 落地，可与 BE-01/FE-01 并行（只改 frontend）｜执行者 fe-2（前端 B）｜审查 reviewer-1

## 1. 目标

落地“交易管理页体系”：`/spaces` 列表（docCount/更新时间/空态）→ `/spaces/[id]` 详情（一键引入 AI 库 + copied/skipped/failed 计数 + 轮询 doc 状态）
→ `/subscriptions` 订阅管理（订阅列表 biz/策略/下次同步 + Job 进度条 5s 轮询 + PARTIAL 时“重试失败 N 篇”）
→ 引入后去 `/chat` 问答验证 citations.spaceName=AI前沿库。只改 frontend，不碰后端。

## 2. 工作目录

`E:/Code/AideanBot`

## 3. 允许改动范围

- `frontend/app/spaces/page.tsx`（列表；仅允许动列表/空态/计数相关段）
- `frontend/app/spaces/[id]/page.tsx`（详情 + 一键引入 + 进度；仅允许动引入/进度相关段）
- `frontend/app/subscriptions/page.tsx`（订阅管理页；允许完整实现本页）
- `frontend/app/public/page.tsx`（仅允许为引入闭环补必要的展示参数，禁止改路由结构）
- `frontend/components/PublicLibraryPicker.tsx`（只读复用为主；确需改动必须先 BLOCKED 请示）
- `frontend/lib/api.ts`（仅允许为上述页面补已存在后端端点的调用封装，禁止新增后端契约假设）
- `frontend/tests/fe02-spaces-subs.test.tsx`（新建，≥2 个组件测试）
- `E:/Code/AideanCompany/fleet/projects/AideanBot/FE-02/` 下的任务包与证据索引

## 4. 禁止改动

- 不改 `backend/` 任何文件。
- 不改 `frontend/app/onboarding/**`、`frontend/app/chat/**`、`frontend/app/page.tsx`（归 FE-01）。
- 不改 `TopBar.tsx`（归 FE-01），本包如需入口请在页面内链，不碰顶栏。
- 不引外部 CDN；不改 Fleet 状态；不 commit、不 push。

## 5. 依赖

- T-017 P1 契约：`GET /spaces/public`、`POST /spaces/{id}/links`、AI前沿库探针现状。
- T-018 P2 契约：sources/subscriptions/jobs/retry 端点现状（只读调用）。
- 缺失契约标“待确认”，不自造接口。

## 6. 实现范围

1. `/spaces`：列表渲染 + docCount/更新时间 + 空态引导 + 错误重试。
2. `/spaces/[id]`：一键引入 AI 库按钮 + copied/skipped/failed 计数 + doc 状态轮询（5s）+ 引入后去问答入口。
3. `/subscriptions`：订阅列表 + Job 进度条（5s 轮询 `GET /jobs/{id}`）+ PARTIAL 时重试按钮（`POST /jobs/{id}/retry`）。
4. 闭环验证位：引入后 citations.spaceName 展示位预留（真实 SSE 帧验证归 worker-c 回归）。
5. 组件测试 ≥2 个（引入进度 + 订阅重试或列表空态）。

## 7. 验收命令清单

```bash
cd E:/Code/AideanBot/frontend && npx tsc --noEmit
cd E:/Code/AideanBot/frontend && npx vitest run tests/fe02-spaces-subs.test.tsx
cd E:/Code/AideanBot/frontend && npx vitest run
```

## 8. 证据路径

- CLI transcript：`E:/Code/AideanBot/.workbuddy/evidence/FE-02-cli.log`
- 运行证据：`E:/Code/AideanBot/.workbuddy/evidence/fe02_run_20260914.txt`
- 测试文件：`E:/Code/AideanBot/frontend/tests/fe02-spaces-subs.test.tsx`

## 9. CLI 委托（本包强制）

```text
delegate_to: opencode run "<本包全文 + SOUL 六节报告要求 + CLI 证据要求>" --dir E:/Code/AideanBot -m nvidia/nvidia-nemotron-3-ultra-550b-a55b
```

cwd=`E:/Code/AideanBot`。CLI 全量输出落 `FE-02-cli.log`。

## 10. 报告格式

SOUL 六节 + 模型自述（含 CLI/模型/命令/cwd/exit）+ CLI 证据要求。阻塞回 BLOCKED。

## 11. 重试上限

机器门失败 REWORK 上限 3 次；第 3 次仍失败标 ESCALATED。

## 12. 完成标准（机器门）

- 3 条验收命令退出码全 0；新增测试 ≥2 个全过且全量 vitest 无回归；
- `FE-02-cli.log` 与 `fe02_run_20260914.txt` 落盘；
- reviewer-1 独立审查 PASS/PARTIAL。

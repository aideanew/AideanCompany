# BE-01 · 订阅执行引擎端到端闭环

> 项目：AideanBot（P-004）｜关键路径｜串行首发｜执行者 worker-b（后端 A）｜审查 reviewer-1

## 1. 目标

把 T-018 已落地的订阅编排（sources/subscriptions/jobs 端点 + Manifest Diff + JobItem 状态机）真正跑通为
“订阅 → Job(sync_account) → JobItem 逐篇走 P0 单篇流水线 → Job 终态 SUCCEEDED/PARTIAL_SUCCESS(30005)”的端到端闭环。
当前缺口（T-021 defects D-05）：JobItem 状态机通，但逐篇 ingest 执行循环未接线（归 M3）。
本包要求补齐该执行循环（允许新增 `backend/app/services/subscription_runner.py` 或在 `subscription.py` 内增量补齐，
二选一，禁止两处各写一套），并用可重复的运行证据证明闭环。

## 2. 工作目录

`E:/Code/AideanBot`

## 3. 允许改动范围

- `backend/app/services/subscription_runner.py`（新建，推荐）或 `backend/app/services/subscription.py`（增量，二选一）
- `backend/app/services/jobs.py`（仅允许补 transition/heartbeat 调用，禁止改状态机定义）
- `backend/app/services/state_machine.py`（仅允许补缺失的合法流转边，需在报告说明理由；不得放宽非法流转）
- `backend/app/api/v1/subscriptions.py`（仅允许为闭环补必要的触发/查询参数，禁止改契约字段名）
- `backend/tests/test_be01_subscription_run.py`（新建，≥4 个用例）
- `E:/Code/AideanCompany/fleet/projects/AideanBot/BE-01/` 下的任务包与证据索引（本包自带目录）

## 4. 禁止改动

- 不改 `frontend/` 任何文件（前端归 FE 包）。
- 不改 `backend/app/services/kb.py` 的 P0 先查后抓语义（只允许调用，禁止改命中/版本逻辑）。
- 不改 Alembic 历史版本；如需新迁移必须单列新版本文件并写回滚说明（且须任务包外先经 Manager 批准）。
- 不改 Fleet 状态（roster/tasks/projects/audit）、不删证据、不 commit、不 push、不写死任何 Key。
- 不得同时改 `subscription_runner.py` 与 `subscription.py` 两套执行循环（二选一）。
- 不得与 BE-03 同改 `jobs.py` 同一函数（BE-01 锁 `submit/transition/heartbeat` 调用点，BE-03 锁重试语义，见依赖）。

## 5. 依赖（已验证，可直接用）

- T-016 P0 资产缓存 DONE（`kb.ingest_url` 先查后抓 + `hit_count` + version 语义）。
- `backend/app/services/subscription.py` 的 register/list/create/list-subscriptions/get_job/retry_job 现状。
- `backend/app/services/jobs.py` 的 submit/transition/heartbeat；`state_machine.py` 的 JOB_DOMAIN 流转表。
- REDFOX 真实 Key 未到位：清单来源用 fixture 打桩并在证据中如实标注（不冒充真实抓取）。

## 6. 实现范围（必须全部交付）

1. 执行循环：对处于 QUEUED/RUNNING 的 Job，逐 JobItem 调用 P0 单篇流水线（`kb.ingest_url`），按结果置 JobItem
   SUCCEEDED/FAILED，Job 终态按规则收敛（全成→SUCCEEDED；有失败→PARTIAL_SUCCESS(30005)；全失败→FAILED）。
2. 幂等：同 `idempotency_key` 重复提交返回原 Job；同 URL 重复 ingest 复用同一 docId（走 P0 缓存语义）。
3. 进度可观测：`GET /jobs/{id}` 返回 items 进度（总数/成功/失败/待跑），失败项带 `error` 原文。
4. 单篇重试：`POST /jobs/{id}/retry` 仅对 FAILED 项重跑，重跑后重算 Job 终态。
5. 单测 `test_be01_subscription_run.py` ≥4 个：全成功收敛 SUCCEEDED／部分失败收敛 PARTIAL_SUCCESS／幂等复用／retry 后重算终态。

## 7. 验收命令清单（逐条真跑，原文贴报告）

```bash
cd E:/Code/AideanBot && python -m ruff check backend
cd E:/Code/AideanBot && python -m mypy backend/app/services/subscription_runner.py backend/app/services/subscription.py backend/app/services/jobs.py
cd E:/Code/AideanBot && python -m pytest backend/tests/test_be01_subscription_run.py -q
cd E:/Code/AideanBot && python -m pytest backend/tests -q
```

## 8. 证据路径

- CLI transcript：`E:/Code/AideanBot/.workbuddy/evidence/BE-01-cli.log`
- 运行证据：`E:/Code/AideanBot/.workbuddy/evidence/be01_run_20260914.txt`（测试输出 + Job 状态流转摘录）
- 单测文件：`E:/Code/AideanBot/backend/tests/test_be01_subscription_run.py`

## 9. CLI 委托（本包强制）

```text
delegate_to: claude -p "<本包全文 + SOUL 六节报告要求 + CLI 证据要求>" --output-format text --permission-mode acceptEdits --add-dir E:/Code/AideanBot
```

cwd=`E:/Code/AideanBot`。CLI 全量输出落 `BE-01-cli.log`。无 transcript 不得判 DONE。

## 10. 报告格式

SOUL 六节 + 模型自述（含 CLI/模型/命令/cwd/exit）+ CLI 证据要求（见 `fleet/configs/cli-delegation.md §4`）。
阻塞时回 `BLOCKED + 精确阻塞点 + 需要谁提供什么`，不得编造完成。

## 11. 重试上限

机器门失败 REWORK 上限 3 次；第 3 次仍失败标 ESCALATED 上报并附全部证据。

## 12. 完成标准（机器门）

- 4 条验收命令退出码全 0；
- `test_be01_subscription_run.py` ≥4 用例全过且全量 `pytest` 无回归；
- `BE-01-cli.log` 与 `be01_run_20260914.txt` 落盘且含命令/cwd/时间戳/exit/输出；
- reviewer-1 独立审查 PASS/PARTIAL（只审不改）。

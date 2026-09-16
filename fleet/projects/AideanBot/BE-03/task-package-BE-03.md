# BE-03 · SaaS 集成 P3（前置 BE-01，引擎路由收敛）

> 项目：AideanBot（P-004）｜关键路径之后（BE-01 DONE 方可开工）｜执行者 be-2（后端 B，主；be-3 为备用/并行子模块）｜审查 reviewer-1

## 1. 目标

在 BE-01 订阅闭环 DONE 的基础上，完成 SaaS 集成 P3：以 `KnowledgeEnginePort` 为唯一契约，
收敛 LangBot（builtin）现行调用，并让 RAGFlow/Coze/Dify/FastGPT 按“Key 到位逐个接”的纪律真实可用或如实不可用。
Key 未到位的引擎必须返回明确不可用（403 + “请联系管理员配置”口径），禁止假装可用。

## 2. 工作目录

`E:/Code/AideanBot`

## 3. 允许改动范围

- `backend/app/providers/engine_port.py`（端口定义；仅允许补缺失方法签名，需说明理由）
- `backend/app/providers/langbot_adapter.py`（行为零变更搬运；仅允许等价重构）
- `backend/app/providers/ragflow_adapter.py`（骨架→真实接线，Key 走 env）
- `backend/app/providers/saas_adapters.py`（新建或增量 Coze/Dify/FastGPT 三家 allowlist + 可用性判定，二选一落一处）
- `backend/app/api/v1/engines.py`（GET /engines 可用性位 + PATCH /spaces/{id}/engine 校验，禁止改字段名）
- `backend/app/core/config.py`（仅允许加 `kb_default_engine/kb_engine_allowlist/*_api_key/*_api_base` 占位，值走 env）
- `backend/tests/test_be03_saas_routing.py`（新建，≥3 个用例）
- `E:/Code/AideanCompany/fleet/projects/AideanBot/BE-03/` 下的任务包与证据索引

## 4. 禁止改动

- 不改 `frontend/`（前端归 FE 包）。
- 不改 BE-01 的执行循环文件（`subscription_runner.py` 或 `subscription.py` 执行段，二者以 BE-01 实际落点为准，只读调用）。
- 不改 `jobs.py` 的状态机定义；与 BE-01 同改 `jobs.py` 时只允许动重试语义函数（BE-01 锁调用点，互斥）。
- 不改 Alembic 历史版本；不写死任何 Key 到代码/文档；不 commit、不 push、不改 Fleet 状态。

## 5. 依赖（BE-01 DONE 后开工）

- BE-01 DONE：订阅执行循环已闭环（否则本包 BLOCKED，依赖项=BE-01）。
- T-019 P4 引擎可插拔现状（`engine_port.py` + LangBotAdapter + Ragflow 骨架 + engines 端点）。
- SaaS Key 现状：以 `GET /engines` 的 `configured` 位为准；未配 Key 的引擎只验“明确不可用”路径。

## 6. 实现范围

1. 端口收敛：所有引擎调用经 `KnowledgeEnginePort` 六方法（create_kb/upload_file/ingest_status/retrieve/delete_kb/delete_file），
   现状直调 LangBot 处收敛到 `LangBotAdapter`，行为零变更（202→READY→SSE 回归一致）。
2. 可用性诚实：`GET /engines` 返回 5 引擎位 + `configured`；`PATCH /spaces/{id}/engine` 对未配 Key 的引擎返回 403 + 提示语；
   空间视图与 SSE citations 追加 engine 字段（沿用 T-019 契约，不得改名）。
3. 单测 `test_be03_saas_routing.py` ≥3 个：builtin 全程可用／未配 Key 的引擎 403／allowlist 外引擎拒绝。

## 7. 验收命令清单

```bash
cd E:/Code/AideanBot && python -m ruff check backend
cd E:/Code/AideanBot && python -m mypy backend/app/providers backend/app/api/v1/engines.py
cd E:/Code/AideanBot && python -m pytest backend/tests/test_be03_saas_routing.py -q
cd E:/Code/AideanBot && python -m pytest backend/tests -q
```

## 8. 证据路径

- CLI transcript：`E:/Code/AideanBot/.workbuddy/evidence/BE-03-cli.log`
- 运行证据：`E:/Code/AideanBot/.workbuddy/evidence/be03_run_20260914.txt`
- 单测文件：`E:/Code/AideanBot/backend/tests/test_be03_saas_routing.py`

## 9. CLI 委托（本包强制）

```text
delegate_to: codex exec --skip-git-repo-check -C E:/Code/AideanBot -s workspace-write "<本包全文 + SOUL 六节报告要求 + CLI 证据要求>"
```

cwd=`E:/Code/AideanBot`。CLI 全量输出落 `BE-03-cli.log`。be-3 仅在 Manager 拆出可并行子模块时启用同命令，禁止双人同改一文件。

## 10. 报告格式

SOUL 六节 + 模型自述（含 CLI/模型/命令/cwd/exit）+ CLI 证据要求。阻塞回 BLOCKED + 精确阻塞点。

## 11. 重试上限

机器门失败 REWORK 上限 3 次；第 3 次仍失败标 ESCALATED。

## 12. 完成标准（机器门）

- 4 条验收命令退出码全 0；`test_be03_saas_routing.py` ≥3 用例全过且全量 pytest 无回归；
- `BE-03-cli.log` 与 `be03_run_20260914.txt` 落盘；
- reviewer-1 独立审查 PASS/PARTIAL。

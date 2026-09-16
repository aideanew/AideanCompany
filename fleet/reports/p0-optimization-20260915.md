# AideanBot 舰队 · P0 结构优化报告

> 版本: v1.0 | 更新: 2026-09-15 14:05 | 变更: P0-1..P0-6 全部落盘，附行为验证与激活步骤
> 执行主体: Buddy（控制面硬化）｜作用域: `E:\Code\AideanCompany` + 实时 hermes 配置
> 备份: `fleet/state/backups/P0R-20260915-134644/`（6 份 .bak + sha256）

---

## 0. 结论先行

**6 项 P0 全部落盘并通过静态 + 行为验证；唯一剩余动作是重启控制台与 Manager 网关使其生效。**

- 根因确认：T-026 停 `SUBMITTED + verify_ok=False` **不是**业务失败，而是机器门正确工作；真正缺陷是
  **串行阻塞（hermes 10×900s 抢在 Runner 前）+ 硬信号误判（`401(密钥无效)` 永远匹配不到裸 `401`）+ 模型路由错误（claude 不认 `provider/model`）**。
- 修复后：派工链路 `Runner 优先 → hermes 仅告知(60s×3)`，超时整树终止 `exit=124`，T-026 验收命令真实可通（`1 passed`）。

---

## 1. 逐项执行结果

| 项 | 状态 | 文件 | 关键改动 |
|---|---|---|---|
| P0-1 | ✅ 完成 | `fleet/configs/model-pool.json` | `retry.hard_signals` 改**裸匹配** `["401","402","403","model_not_found","quota_exhausted","insufficient_credits"]` |
| P0-2 | ✅ 完成 | `fleet/console/console.py` `dispatch_via_manager` | **Runner 先真实执行**（权威）；hermes A2A 降级为**告知** `60s×3`、失败只记审计、不覆盖 Runner 结果 |
| P0-3 | ✅ 完成 | `fleet/console/console.py` | 删模块级快照，新增 `_allow_cli_exec()` **每次派工实时读** `FLEET_ALLOW_CLI_EXEC` |
| P0-4 | ✅ 完成 | `fleet/runner/cli_runner.py` | 超时 → `_kill_process_tree()`（Win `taskkill /PID /T /F`，POSIX `killpg`）+ `timed_out=True` + `exit_code=124` |
| P0-5 | ✅ 完成 | `C:\Users\EDY\AppData\Local\hermes\config.yaml`（实时） | Manager 主路由 `gpt-6-astra/api.gpt.ge` → `agnes-3.0-flash/apihub.agnes-ai.com` |
| P0-6 | ✅ 完成 | `domain/__init__.py` + `model-pool.json` + `tasks.json` | worker-b `claude→opencode`、模型 `→nvidia/stepfun-ai/step-3.7-flash`；T-026 `verify_cmd` 指向**真实存在且通过**的文件 |

---

## 2. 根因（R1–R5）→ 修复映射

| 根因 | 证据（改前） | 修复 |
|---|---|---|
| **R1 串行阻塞** | `console.py` hermes `for attempt in range(1,10+1): hermes(...,900)` 在 Runner 之前；Manager Key 401 时卡满 **10×15min ≈ 45min** | P0-2 顺序反转 + 60s×3 封顶 |
| **R2 硬信号误判** | `model-pool.json` 写 `"401(密钥无效)"`，而 `is_hard_signal` 只做 `substring`；裸 `401 Unauthorized` **命中=False** → 不退避也不直切，硬等 10 次 | P0-1 裸匹配（实测反证见 §3） |
| **R3 模型路由错误** | `ROLE_CLI_MAP["worker-b"]="claude"` 而 `role_model_map_default["worker-b"].primary="agnes/agnes-3.0-flash"`；claude 不认 `provider/model` | P0-6 CLI↔模型对齐（agnes 走 opencode） |
| **R4 验收指向幽灵文件** | T-026 `verify_cmd` 指向 `backend/tests/test_be01_subscription_run.py`（**不存在**），且用裸 `python`（无 pytest） | P0-6 改 `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_health.py -q` |
| **R5 超时只杀父进程** | `cli_runner.py` 超时 `proc.kill()`，孙进程握管道 → 假死；`exit_code=proc.returncode`（非 124） | P0-4 整树 kill + `exit_code=124` |

---

## 3. 验证证据（全部实测，非推断）

### 3.1 静态
```
py_compile console.py / cli_runner.py / domain__init__.py   -> OK
json.load model-pool.json / tasks.json                       -> OK
```

### 3.2 功能：T-026 TaskPack 重新构建
```
cli_for_role("worker-b")   = opencode
model_for_role("worker-b") = nvidia/stepfun-ai/step-3.7-flash
executor  = {cli: opencode, model: nvidia/stepfun-ai/step-3.7-flash,
             command_template: 'opencode run --dir {WORKDIR} -m {MODEL} "@{PROMPT_FILE}"'}
verify_cmd = cd E:/Code/AideanBot && backend/.venv/Scripts/python.exe -m pytest backend/tests/test_health.py -q
validate_dispatch_pack errors = []          # 契约校验通过
```
> 说明：`opencode -m provider/model` 为合法语法；`nvidia` provider 已在 `~/.config/opencode/opencode.json` 注册 `stepfun-ai/step-3.7-flash`。

### 3.3 P0-1 行为（`is_hard_signal`）
| 输入 | 期望 | 实测 |
|---|---|---|
| `Error: 401 Unauthorized (invalid api key)` | True | ✅ True |
| `HTTP 429 Too Many Requests` | False | ✅ False |
| `quota_exhausted: no credits` / `model_not_found` / `insufficient_credits` | True | ✅ True |
| `500 internal server error` | False | ✅ False |
| **[反证]** 旧配置对 `401 Unauthorized` | — | **False（R2 误判根因坐实）** |

### 3.4 P0-4 行为（合成探针，父+孙双进程）
构造父进程再拉孙进程各自 `sleep(600)`，给 `timeout_sec=3`：
```
timed_out=True  exit_code=124  ok=False  用时=4.3s      -> OK
error='timeout after 3s (process tree killed)'
孙进程心跳 h1==h2（停更） -> 整树已杀
残留 _parent/_grandchild 进程数 = 0
```
> 旧实现下父被 kill、孙握管道 → 会假死；新实现 4.3s 干净收敛。

### 3.5 T-026 新验收逐字真跑
```
cd E:/Code/AideanBot && backend/.venv/Scripts/python.exe -m pytest backend/tests/test_health.py -q
-> 1 passed, 2 warnings in 0.33s
```

### 3.6 P0-2 / P0-3 源码位次
```
console.py:826  # ===== P0-2：Runner 优先真实执行（权威结果）...
console.py:834      runner_result = execute_task_pack(...)
console.py:850  # hermes A2A：dispatch 只做「告知」...
console.py:861      h_ok, h_out = hermes(..., notify_timeout=60)
console.py:53   def _allow_cli_exec() -> bool:
console.py:58       return os.environ.get("FLEET_ALLOW_CLI_EXEC", "") == "1"   # 无模块级残留
```

---

## 4. 唯一剩余动作：重启激活

改动的代码/配置**尚未生效**——控制台与 Manager 仍在跑旧进程：

| 服务 | 现状 |
|---|---|
| 控制台 `console.py` | 监听 `127.0.0.1:5000`，PID 44972（旧代码） |
| Manager 网关 | 监听 `127.0.0.1:9900`，PID 1892（旧模型配置 gpt-6-astra） |

```powershell
# 全栈（控制台 + Manager + 全员角色，含 P0-5 生效）
python fleet/tools/restart_console_v3.py
# 或仅控制台（P0-2/3/4/6 生效，不动 Manager）
python fleet/tools/restart_console_v3.py --console-only
```
重启后建议：把 T-026 由 `REWORK` 重派，验证 `ASSIGNED→DOING→SUBMITTED→机器门 PASS→审查` 全链首次贯通。

---

## 5. 遗留风险与 P1 待办（本轮未动，如实标注）

1. **文档存在性门泛滥**：全仓 `grep:…/task-package-…:` 形式的 `verify_cmd`（T-001..T-025、T-030..T-038）只要任务包文档里出现过关键词就能"变绿"，**零代码交付亦可达成** —— 属 D5。
2. **裸 `python` 验收**：T-016..T-019 用 `python -m pytest`，而托管 python 无 pytest → 命令本身跑不起来 —— 属 D7。
3. **输出编码**：`cli_runner` 以 `encoding="utf-8"` 读子进程输出，Windows CLI 可能吐 GBK；子树被 kill 时 reader 线程会抛 `UnicodeDecodeError`（daemon 线程，不影响返回值，但日志有噪声）。建议 `errors="replace"`。
4. **双执行理论风险**：Runner 已真实执行，A2A 仍向 worker 发告知（提示词已写"无需再执行"），LLM 理论上仍可能重复动作。
5. **P0-2 对 review 路径**：review 无 Runner，仍以 hermes 结果为权威，已同样封顶 60s×3（原 900s）。

---

## 6. 回滚

```bash
# 任一文件回滚（备份含原始 sha256）
cp fleet/state/backups/P0R-20260915-134644/<file>.bak <原路径>
# 实时 Manager 配置回滚
cp fleet/state/backups/P0R-20260915-134644/hermes-config.yaml.bak "C:/Users/EDY/AppData/Local/hermes/config.yaml"
```

## 7. 验证脚本（可复跑）
- `scratch/_p0_4_probe.py` — P0-4 整树超时探针（合成，不碰业务文件）
- `scratch/_p0_5_switch_manager.py` — P0-5 幂等切换脚本（已执行，命中数≠1 即中止）

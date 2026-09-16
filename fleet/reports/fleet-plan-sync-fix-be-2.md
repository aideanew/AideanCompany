# W1 计划/事件同步后端 · 报告（be-2）

生成时间：2026-09-14（UTC+08:00）

### 结论
已完成，等待管理者验收。

### 模型自述
- 模型提供商：b.ai（profile be-2 config：base_url `https://api.b.ai/v1`）
- 模型：`qwen3.8-flash`（provider: custom, api_mode: chat_completions）
- 兜底：本轮未触发 fallback_providers。

### 执行过程
1. 通读 `fleet/console/console.py`（1311 行）与任务目标文件 `fleet/projects/fleet-plan-sync-fix-goal.txt`，确认现状：已有 `project_metrics/project_plan/plan_task_row` 与 15 秒 meta refresh，缺统一事件源与计划编辑接口。
2. 统一事件写入（同状态源）：
   - `audit()` 升级为统一事件入口：新增 `**extra` 结构化字段（from/to/assignee/reviewer/url），带 task 的记录自动附规范 URL（`task_event_url()` → `http://127.0.0.1:5000/tasks/<id>`，仅项目 → `/projects?project=<pid>`）。
   - `transition()`（状态机门）迁移事件自动写 `from/to/assignee/reviewer`。
   - `machine_verify()`（机器验收）、dispatch（派工）、review（送审）、rework（返工）、close（收口）、`update_plan()`（计划修改）全部经同一 `audit()` 落 `state/audit.log`（append-only，可回放）。
3. 只读 API：
   - `GET /api/plan?project=<pid>`：返回 project/name/total/done/remaining/progress/tasks（按当前顺序），每项含 id/state/title/detail/assignee/reviewer/verify_cmd/rework_count/editable/url；项目不存在或缺参数 → 400。
   - `GET /api/events?project=<pid>&since=<序号>&limit=`：audit.log 行号即事件序号，轻量增量；返回 timestamp/actor/action/taskId/from/to/assignee/reviewer/summary/url；`since` 非法 → 400；limit 钳制 1..1000。
   - 防泄漏防线：`_redact()` 对事件 summary/title/detail/verify_cmd 输出前做敏感串脱敏（api_key/sk-*/Bearer/password → `[REDACTED]`）。
4. 计划更新安全接口 `POST /tasks/<tid>/plan`（同 `update_plan()` 可直接调用）：
   - 字段白名单仅 title/detail/verify_cmd/assignee/reviewer/order，含任何禁改字段（state/project/id 等）→ 整体拒绝；
   - 复用既有门：角色流程权限（执行者=worker、审查者=reviewer）、`DENY_RE` 危险命令黑名单（含 grep: 格式校验）、`workspace_allowed` 目录白名单、状态机门（仅 DRAFT/ASSIGNED/REWORK/PARTIAL/FAILED/BLOCKED 可编辑，DOING/SUBMITTED/REVIEWING/DONE 拒绝）；字段长度上限；order 仅项目内重排并钳制越界；
   - 每次成功修改写 `plan_updated` 审计事件（含 URL），append-only 审计不可改。
5. 网页编辑入口（仅模板边界，未加任何前端实时同步脚本）：`GET /tasks/<tid>/plan-edit` 编辑表单页（不可编辑状态显示拒绝页）；计划大纲 `plan_task_row` 与任务详情页在可编辑状态下增加"✏️ 编辑计划"链接。
6. 派工/送审/返工/收口的网页回执提示统一附可访问 URL（任务详情、项目看板、事件流 `/api/events`）。

### 改动文件清单
| 文件 | 改动 |
|---|---|
| `fleet/console/console.py` | W1 全部后端改动（事件统一、/api/plan、/api/events、update_plan、plan-edit 页面与路由、提示附 URL） |
| `fleet/console/tests/test_plan_api_w1.py` | 新增：14 项隔离测试（tempdir 数据 + 临时端口，不触碰生产 state） |
| `fleet/console/tests/w1_manual_smoke.py` | 新增：手工冒烟脚本（打印真实响应供证据引用，测完自清理） |
| `fleet/reports/fleet-plan-sync-fix-be-2.md` | 本报告 |

### 验证记录
1. `python -m py_compile fleet/console/console.py`
```
COMPILE_OK
（另有 SyntaxWarning: invalid escape sequence '\D'（1131 行附近）——经对 HEAD 版本
 py_compile 比对确认为存量告警，非本次引入）
```
2. 隔离测试 `PYTHONUTF8=1 python fleet/console/tests/test_plan_api_w1.py`
```
Ran 14 tests in 0.771s

OK
```
覆盖：plan 总数/完成/剩余/百分比与明细字段、非法项目 400；事件增量 since、from/to/actor/taskId/url、密钥脱敏、非法 since 400；计划字段可编辑、禁改 state/project/id 整体拒绝、危险 verify_cmd 拒绝、角色权限校验、状态机门拒绝、order 项目内重排+越界钳制、编辑入口页面存在性。
3. `git diff --check`
```
$ git diff --check -- fleet/console/console.py fleet/console/tests
our-files-exit=0        ← 本次改动文件 0 告警

$ git diff --check      （全仓）
fleet/console/logs/worker-c-start.log:72/92/94/100: trailing whitespace.
diff-check-exit=2       ← 全部来自他人已跟踪的日志文件（worker-c-start.log 等），
                          非本次改动引入，不在 W1 允许改动范围内，未处理。
```

### 证据链
1. 冒烟 `PYTHONUTF8=1 python fleet/console/tests/w1_manual_smoke.py`（隔离临时数据，端口自动分配）原样输出：
```
GET /api/plan?project=P-001
  -> HTTP 200
  {"project": "P-001", "name": "冒烟项目", "total": 1, "done": 0, "remaining": 1, "progress": 0,
   "url": "http://127.0.0.1:62015/projects?project=P-001",
   "tasks": [{"id": "T-001", "title": "冒烟任务", "state": "ASSIGNED", "detail": "目标",
              "assignee": "be-2x", "reviewer": "rv-1x", "verify_cmd": "grep:a.txt:foo",
              "rework_count": 0, "editable": true,
              "url": "http://127.0.0.1:62015/tasks/T-001"}]}

GET /api/events?project=P-001&since=0
  -> HTTP 200
  {"seq": 2, "project": "P-001", "events": [{"seq": 1, "timestamp": "2026-09-14 13:04:13",
    "actor": "console", "action": "state:ASSIGNED", "taskId": "T-001",
    "from": "DRAFT", "to": "ASSIGNED", "assignee": "be-2x", "reviewer": "rv-1x",
    "summary": "派工", "url": "http://127.0.0.1:5000/tasks/T-001"}, {"seq": 2, ..., "action": "dispatch", ...]}

GET /api/plan?project=NOPE
  -> HTTP 400
  {"error": "缺少 project 参数或项目不存在"}

GET /api/events?since=abc
  -> HTTP 400
  {"error": "since 必须是整数序号"}

POST /tasks/T-001/plan (verify_cmd=rm -rf / 危险命令)
  -> HTTP 200 | 页面含拒绝: True
cleanup done
```
2. 生产 state 未被测试污染：测试后 `tail -1 fleet/console/state/audit.log` 仍为存量记录（`2026-09-13 23:40:00 ... state:DONE T-015`），`state/evidence/` 无新增文件。
3. 任务详情 URL 契约：事件 `url` 字段统一为 `http://127.0.0.1:5000/tasks/<id>`（生产 CONSOLE_BASE）；冒烟中脚本为自证覆盖为临时端口。

### 未完成事项与风险
1. **生产 5000 端口服务未重启**：端口 5000 上现有 console 进程为管理者/其他角色所启，W1 范围不含重启；新 API 需进程重启后生效（建议管理者在 W2 联调前重启一次）。
2. 旧 audit.log 存量行无 `url/from/to` 字段，`/api/events` 已按 taskId→项目映射实时补全 url，from/to 为空串——历史事件可读但不含迁移细节（设计内降级，未迁移数据）。
3. `plan_updated` 记录的是"改了哪些字段名"，不存改前值快照（audit 保持轻量 append-only）；如需字段级回放需后续加 diff 字段。
4. `dispatch_via_manager` 后台线程内的回执/判定事件沿用 `transition()` 统一写入，未单独加 dispatch_reply 结构化字段（既有 `manager dispatch_reply/review_reply` audit 行保留，事件流可见）。
5. W2/W3 边界：本任务未动 meta refresh 与任何前端实时脚本；`git diff --check` 全仓告警来自他人日志文件，需管理者决定是否纳入 .gitignore。

判定：PASS（W1 范围内验收命令全部实测通过）

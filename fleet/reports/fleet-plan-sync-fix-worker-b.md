# W1 统一计划/事件 API 后端 · 修复验收报告（worker-b）

生成时间：2026-09-14（UTC+08:00）
任务包：fleet-plan-sync-fix W1（目标文件 E:/Code/AideanCompany/fleet/fleet/console/console.py，实际仓库布局为 E:/Code/AideanCompany/fleet/console/console.py，git 差异路径 fleet/console/console.py 与任务包一致）

### 结论
已完成，等待管理者验收。
（说明：W1 主体实现已存在于工作区未提交差异中（be-2 首轮产出，+318 行）；本轮 worker-b 按任务包做了全量契约复核 + 2 处修复 + 新增 45 项隔离测试，全部通过。）

### 模型自述
- 模型提供商：b.ai（profile worker-b config：base_url `https://api.b.ai/v1`）
- 模型：`qwen3.8-flash`（provider: custom, api_mode: chat_completions）
- 兜底：本轮未触发 fallback_providers（全程同一平台，无切换）。

### 执行过程
1. **契约复核**（逐项对照任务包 W1）：
   - `GET /api/plan?project=<pid>`：返回 project/total/done/remaining/progress/tasks（按当前顺序），每项含 state/detail/assignee/reviewer/verify_cmd/rework_count/editable/url ✔
   - `GET /api/events?project=&since=<序号>&limit=`：以 audit.log 行号为事件序号，轻量增量；返回 timestamp/actor/action/taskId/from/to/assignee/reviewer/summary/url；since 非法 → 400；limit 钳制 1..1000 ✔
   - 统一事件写入：`audit()` 为唯一入口，transition（状态迁移含 from/to）、machine_verify（机器验收）、dispatch（派工）、review（送审）、rework（返工）、close（收口）、plan_updated（计划修改）均落 `state/audit.log`（append-only 可回放）；每条带 task 的事件自动生成 `http://127.0.0.1:5000/tasks/<id>`，仅项目则 `…/projects?project=<pid>` ✔
   - 计划更新安全接口 `POST /tasks/<tid>/plan` + 同构函数 `update_plan()`：字段白名单仅 title/detail/verify_cmd/assignee/reviewer/order；含 state/project/id 等即整体拒绝；复用角色流程权限（执行者=worker/审查者=reviewer）、DENY_RE 危险命令黑名单、workspace_allowed 目录白名单、状态机门（仅 DRAFT/ASSIGNED/REWORK/PARTIAL/FAILED/BLOCKED 可编辑）；不删任务；修改全程审计 ✔
   - 网页编辑入口：`GET /tasks/<tid>/plan-edit` 表单页（不可编辑态显示拒绝页）；计划大纲与任务详情页均有「✏️ 编辑计划」链接 ✔
   - 防 Key 泄漏：`_redact()` 对 api_key/sk-*/Bearer/password 命中即 `[REDACTED]` ✔
2. **修复 1（py_compile 告警）**：console.py:1124 placeholder 字符串含非法转义 `\D`，导致 `python -m py_compile` 输出 SyntaxWarning（在 `-W error::SyntaxWarning` 下直接失败）。改为 `E:\\Demo\\Test0912` 合法转义。
3. **修复 2（事件 URL 覆盖缺口）**：`project_created` 审计事件因 task_id 位传的是 pid，未自动生成 URL——显式补 `url=task_event_url(project_id=pid)`，保证"每个事件必须能生成任务详情 URL 或项目 URL"逐条成立。
4. **新增隔离测试** `console/tests/test_plan_events_w1.py`（45 项断言）：import console 模块并把 STATE/tasks/projects/roster/audit 全部 patch 到临时目录，HTTP 用临时端口 5399，不触碰生产状态与 :5000 服务；覆盖 plan_api 口径、事件增量/字段/过滤/脱敏/URL、update_plan 全部安全门（禁改字段、权限、黑名单、状态机门、必填、超长、order 重排、append-only）、HTTP 路由成功/非法路径、编辑入口页面、派工/送审提示 URL。
5. 未做（边界内排除）：前端实时逻辑（W2）、真实派发/验收业务写请求、删除文件/库、git commit/push、模型 Key 变更——均零触碰。

### 改动文件清单
| 文件 | 改动 |
|---|---|
| `fleet/console/console.py` | 2 处修复：L1124 非法转义 `\D` → `\\D`；`project_created` 审计事件补项目 URL。其余 W1 实现为工作区既有差异，本轮复核未回退 |
| `fleet/console/tests/test_plan_events_w1.py` | 新增（45 项隔离测试，纯标准库零依赖） |
| `reports/fleet-plan-sync-fix-worker-b.md` | 本报告 |

### 验证记录
验收命令原样输出（完整逐条 PASS 清单见 `reports/_w1_acceptance_out.txt`）：

```
$ python -W error::SyntaxWarning -m py_compile console/console.py && echo PY_COMPILE_OK
PY_COMPILE_OK            (exit_code=0；修复前的裸 py_compile 曾报
                          SyntaxWarning: console/console.py:1131 invalid escape sequence '\D')

$ python console/tests/test_plan_events_w1.py
✅ PASS plan_api 返回 total/done/remaining 正确 | (3, 1, 2)
✅ PASS plan_api progress 与 project_metrics 口径一致（百分比取整）
✅ PASS plan_api 任务含 state/detail/assignee/reviewer/verify_cmd/rework_count
✅ PASS plan_api 每任务与项目带 URL | http://127.0.0.1:5000/tasks/T-901
✅ PASS plan_api 未知项目返回 None
✅ PASS plan_api editable 门：DONE/DOING 不可编辑、DRAFT 可编辑
✅ PASS 状态迁移写入事件含 from/to/actor/taskId
✅ PASS 事件自带任务详情 URL | http://127.0.0.1:5000/tasks/T-903
✅ PASS 机器验收写入事件 actor=machine-gate
✅ PASS since 增量只返回新事件
✅ PASS read_events 按 project 过滤
✅ PASS 事件摘要脱敏疑似 Key | [REDACTED]
✅ PASS DONE 态禁止编辑（状态机门）
✅ PASS 提交 state 字段被白名单拒绝 | 禁止修改字段：['state']（仅允许 title/detail/verify_cmd/assignee/reviewer/order）
✅ PASS 提交 project 字段被白名单拒绝 / 提交 id 字段被白名单拒绝
✅ PASS 执行者必须是 worker 角色（权限门） / 审查者必须是 reviewer 角色（权限门）
✅ PASS 危险 verify_cmd 被黑名单拒绝 | verify_cmd 命中危险命令黑名单
✅ PASS title 不允许清空（必填校验） / title 超长被拒 / 任务不存在返回失败
✅ PASS 合法字段更新成功且落盘 | 计划已更新：detail, reviewer
✅ PASS 修改前审计字节不变（append-only 可回放）
✅ PASS plan_updated 事件含 actor/fields/URL
✅ PASS order 重排生效（0 起插入） | ['T-913', 'T-911', 'T-912'] / order 非整数被拒
✅ PASS 全程无任务被删除
✅ PASS HTTP GET /api/plan 200+JSON 结构齐全 | 200
✅ PASS HTTP GET /api/plan 缺 project → 400 / 未知项目 → 400
✅ PASS HTTP GET /api/events 200 且含 seq/events
✅ PASS 事件字段齐全 timestamp/actor/action/taskId/from/to/assignee/reviewer/summary/url
✅ PASS HTTP /api/events since 非整数 → 400 / since=当前 seq 增量返回空
✅ PASS 网页编辑入口 200 且含表单/白名单说明
✅ PASS HTTP POST 计划更新：夹带 state 被拒并回显原因
✅ PASS HTTP POST 计划更新：合法修改成功 / 危险 verify_cmd 经网页路径同样被拒
✅ PASS HTTP 修改后状态源同步（tasks.json 已更新）
✅ PASS /projects 页计划行含编辑入口链接
✅ PASS 派工成功提示含事件流+任务 URL / 送审成功提示含事件流+任务 URL
✅ PASS CONSOLE_BASE 指向 5000 且 task_event_url 生成 /tasks/<id>
===== 结果：45 通过 / 0 失败 =====   (exit_code=0)

$ git diff --check -- console/console.py && echo DIFF_CHECK_OK
DIFF_CHECK_OK              (exit_code=0)
```

端口/进程纪律：本轮未启动任何常驻服务（测试内临时 HTTP 服务在 :5399，测试结束 srv.shutdown() 并清理临时目录）；生产 :5000 服务（PID 54488）非本轮启动，未动。

### 证据链
1. 任务包契约来源：`projects/fleet-plan-sync-fix-goal.txt`（W1 四条要求原文）。
2. 实现来源（工作区既有未提交差异 + 本轮修复）：`git diff --stat console/console.py` → `318 insertions`（修复前基线）；关键位置：`audit()` L98-109、`task_event_url()` L91-96、`_redact()` L84-89、`plan_api()` L761、`read_events()` L782、`update_plan()` L810、`page_plan_edit()` L886、路由 `/api/plan` `/api/events` `/tasks/<id>/plan-edit` `/tasks/<id>/plan`（do_GET/do_POST）。
3. 本轮 2 处修复的 diff 均已在 patch 工具输出中留痕（L1124 转义、L1421 project_created url）。
4. 45 项测试原样输出：`reports/_w1_acceptance_out.txt`（三份命令的完整 stdout+exit_code）。
5. 生产 :5000 现运行进程仍是旧代码（`/api/plan` 返回 404 页面，实测 `curl` → 404），需 Manager 重启控制台后新 API 才对生产生效——已列入下节。

### 未完成事项与风险
1. **生产 :5000 控制台进程（PID 54488）运行的是修复前代码**，`/api/plan`、`/api/events` 线上返回 404（实测证据见上）。是否重启由管理者决定（重启会中断网页会话并触发 console_started 审计，非我职权范围，未擅自操作）。
2. 送审成功提示中的事件流链接为 `/api/events?since=0`（不带 project 参数）——事件本身均带 URL，功能达标；若 W2 需要项目级事件流链接可一并微调（属提示文案，未越权改动）。
3. W2（前端 SSE/轮询）、W3（全量测试）不在本任务包范围，未动。
4. `git diff --check` 对**全仓库**仍有告警，全部来自 `console/logs/*.log`（运行日志既有内容，非本轮改动、非源码）；对 `console/console.py` 单独执行结果为 clean（见验证记录原文）。
5. 隔离测试依赖 `import console` 后 patch 模块级路径常量；若未来 console.py 改为构造期捕获路径，测试夹具需同步调整（已在测试头注释说明）。

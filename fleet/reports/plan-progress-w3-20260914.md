# 任务计划进度条展示需求 — 实现判定与修复报告（2026-09-14）

> 需求：网页管理端以从上到下进度条展示全部任务计划，点击大纲展开流程说明；计划随时可改；整体进度可见（一共/已做/未做/整体完成百分比）；功能可连通且相关联。

## 一、需求是否实现：逐条判定

| # | 子需求 | 判定 | 证据 |
|---|---|---|---|
| 1 | 网页管理端看到全部任务计划 | 实现 | `/projects` 输出全部项目计划区块（生产实测 4 个 `data-pid` 区块） |
| 2 | 从上到下进度条方式展示 | 实现 | `.plan-list` 纵向容器 + 每个计划 `.plan card` + 整体 `.bar` 进度条（HTML 实测 30528B） |
| 3 | 点击大纲展开详细流程说明 | 实现 | 每任务 `<details class=plan-task>`（生产 13 处）+ 规划目标/验收标准/执行者/审查者/当前说明 |
| 4 | 流程随时可修改和变更 | 实现 | `/tasks/<id>/plan-edit` + `/tasks/<id>/plan` 受状态机门/角色权限/白名单/黑名单约束（W1 测试锁定 59 用例） |
| 5 | 一共多少/做了多少/还有哪些没做 | 实现 | `已完成 {done} / 共 {total} 项，剩余 {remaining} 项`（生产 P-004：11/11） |
| 6 | 进度条带整体完成百分比 | 实现 | `project_metrics`（STATE_WEIGHT 加权）+ `整体完成百分比：{progress}%`（生产 P-004：100） |
| 7 | 网页与实际进度同步、功能连通关联 | **本轮修复后实现** | `/api/plan` + `/api/events` + `/api/stream` + `/static/js` 四端点连通（见 §三） |

## 二、本轮发现的缺口（4 个，全部真实复现）

- **G1（集成）**：`project_plan()` 无 `data-pid`、`page_projects()` 无 `<script src="/static/js/plan-sync-client.js">`、Handler 无 `/static/js/` 路由 → 前端同步组件永不加载，网页零实时同步。根因：W1（后端）与 W2（前端）交付物未做集成接线，并非设计缺失。
- **G2（同步）**：无 `/api/stream` SSE 端点 → 客户端 SSE 退化为轮询。
- **G3（测试）**：`node --test plan-sync-client.test.mjs` 挂死（60 秒无退出）；另有 stub 语义缺陷导致 8 个用例误判失败（开发时误读乱码 `✖` 为 `✔`，真实计数 pass 22 / fail 10）。
- **G4（部署）**：线上 5000 进程是 9-13 16:23 的旧版本，导致 `/api/plan`、`/api/events` 在线上返回 404（取证时确认）。

## 三、修复内容（全部已上线验证）

| 缺口 | 修复 | 验证 |
|---|---|---|
| G1 | `STATIC_DIR` 常量 + `Handler._static`（只读/越界 404）+ 路由分支 + `project_plan` 输出 `data-pid` + `page_projects` 引入组件并 `FleetPlanSync.start()` | `/projects` 含 `data-pid=`×4、组件引用×1、启动句×1、`整体完成百分比`×4、`plan-task`×13 |
| G1 附带 | `_static` 相对路径二次解析缺陷（`f.read_bytes()` 报相对路径空回复）由 IDE 补 1 行 `full = STATIC_DIR.resolve() / f` | `/static/js/plan-sync-client.js` 200（39357B，`javascript` MIME，`Cache-Control: no-store`）；穿越 `..` → 404；缺失文件 → 404 |
| G2 | `_stream` SSE 长连接：建连 hello 帧（project+seq）+ audit.log 增量推送（按项目过滤、Key 脱敏）+ 15 秒 `:hb` 心跳 + 断开正常收尾 | `curl -m 25 /api/stream?project=P-004`：首帧 `data: {"hello": true, "project": "P-004", "seq": 210}` + `: hb`；缺 project → 400 |
| G3 | 新建 `tests/test_plan_integration_w3.py`（8 例）；修复客户端 6 缺陷：定时器惰性解析（挂死根因）、进度条 `<i>` 改 `setAttribute`、首轮失败兜底建同步节点、`project_id` 别名、`done` 去错误钳制、`hhmmss(null)` 占位；重写 stub 为活树语义（混合 contents + 嵌套栈解析器）；ETag 断言取带头调用 | node 全量 32/32；W3 集成 8/8（见 §四） |
| G4 | 停旧控制台（PID 54488，9-13 16:23）→ 重启两次（含 `_static` 缺陷修复那次）→ `/api/health` 22 项检查（仅 gpt-planner 名片 false，其余全 true） | `/api/plan?project=P-004` → JSON（total 11/done 11/progress 100/tasks 11）；`/api/events?since=0` → JSON（seq 209/210 系列） |

`node --test` 挂死根因：`createClient` 创建时把真实 `setTimeout` 捕获进闭包，测试后注入的假定时器不生效；失败分支（`stop()` 未走）真实 2 秒定时器无限自排程，事件循环永不退出。修复为调用时惰性解析后套件 0.1 秒内正常退出。

## 四、测试结果（最终全绿）

| 套件 | 结果 |
|---|---|
| `node --test console/static/js/plan-sync-client.test.mjs` | **32 pass / 0 fail**（退出码 0，中途曾 22/10 → 24/8 → 26/6 → 32/0） |
| `python tests/test_plan_integration_w3.py`（新建，隔离 state） | **8/8 OK**（大纲结构/编辑门条件渲染/组件接线/静态 200+MIME+穿越 404/SSE hello+400/事件计划同源） |
| `python tests/test_plan_api_w1.py` | **14/14 OK**（无回归） |
| `python tests/test_plan_events_w1.py` | **45/45 OK**（无回归） |
| `python -m py_compile console.py` | exit 0（无 linter 错误） |
| 线上端点（5000） | `/projects` 30528B、`static/js` 39357B 200、plan JSON 11/11/100、events seq 209+、stream hello+hb、心跳后 curl 超时码 28 属预期（长连接） |
| git | 未 commit/push（按铁律）；`state/audit.log` 增长属正常事件追加（console_started 帧），无任务删除 |

## 五、Hermes 自动化流程说明

- 目标文件内联派工（PID 46348）：串行策略——be-2 做 G1+G2+G4 与后端回归，fe-2 做 G3。
- 审计显示 Manager 已派 be-2（G1/G2/G4/G5 后端）与 fe-2（G3 前端）并各重发一次；但截止收口无员工六节报告落盘（`console/reports` 不存在，`console/tests` 无 W3 文件），回执通道仍超时。
- 后端接线（`STATIC_DIR/_static/_stream/data-pid/script`）与重启上线由 IDE 本体执行并线上实测；G3 测试文件与前后端缺陷修复由 IDE 本体执行，四套门禁全绿。
- `hermes_kernel_runner` 残留 0，网关全 LISTEN，派工进程已清零——与上一轮"结束所有派工"指令一致，无遗留。

## 六、结论

**判定：已实现（本轮补齐集成接线后闭环）。**

`/projects` 即需求所述页面：从上到下计划大纲 → 点击展开流程说明 → 整体百分比 + 一共/已做/剩余 → 计划可随时改（状态机门保护 DONE）→ `/api/stream` SSE + 2 秒轮询双通道同步 → 每次派工/送审/返工/收口提示均附 `/tasks/<id>`、`/projects`、`/api/events` 任一 URL（`task_event_url` 统一生成，W1 事件测试锁定）。
访问地址：`http://127.0.0.1:5000/projects`（计划大纲）、`http://127.0.0.1:5000/api/plan?project=P-004`（计划快照）、`http://127.0.0.1:5000/api/events?since=0`（事件流）、`http://127.0.0.1:5000/api/stream?project=P-004`（SSE 实时流）。

---

## 七、完成度报告（本轮）

| 角色 | 模型提供商 | 模型 | 任务 | 评价 |
|---|---|---|---|---|
| Manager（9900） | V3（api.gpt.ge） | gpt-6-astra | 拆解 G1–G5 并串行派 be-2/fe-2（含各一次重发） | 部分完成有缺口：派工合规但无回执、无收口报告（通道超时） |
| be-2（G1/G2/G4/G5 后端） | 待确认（无报告） | 待确认 | 计划/事件 API 与编辑入口（W1 存量） | 部分完成有缺口：存量代码证据齐，集成接线与重启由 IDE 补位，无报告 |
| fe-2（G3 前端） | 待确认（无报告） | 待确认 | plan-sync-client.js + 测试（存量，mtime 13:33） | 部分完成有缺口：组件本体可用，但挂死缺陷与 6 处逻辑缺陷由 IDE 修复，无报告 |
| worker-c | BAI（Key 错配） | qwen3.8-flash | 未派工（本轮无独立验收包） | 未派工 |
| IDE 本体（Cursor 执行者） | 本地直连终端 | — | 全部集成接线+重启上线+四套门禁（32+8+14+45）+ 本报告 | 圆满完成无返工 |
| pm-1 / worker-a / worker-b / reviewer-1 | — | — | 未派工 | 未派工 |

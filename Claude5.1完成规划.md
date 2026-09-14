# Hermes 多 Agent 全自动开发系统：Win11 小白最小原子级可执行方案（以E:\Demo项目为例）

> 适用你现在的状态：`Win11 + Hermes v0.21.1 已安装 + E:\Demo\Temp 工作区 + 完全小白`
> 目标：先打通 `Manager(Hermes) → A2A → Worker → Result → Review → Rework` 最小闭环，再扩展成 AI 软件团队。
> 方法：每一步都是 **目的 / 操作 / 复制粘贴命令 / 预期输出 / 验证 / 失败怎么办**。做完一步，打勾再往下走。

---

## 0. 先理解 3 个概念（30秒看懂）

```text
Manager = 包工头 + 技术经理，只管分活、验收、返工，不自己把所有代码写完
Worker  = 水电工/木工，只干自己专业的活，干完必须交“施工报告+证据”
A2A     = 包工头给工人打电话的协议：发现工人→看名片→派活→收结果
MCP     = 工人的工具箱：文件、终端、浏览器、Git、数据库
```

成功标准只有一条，不是“工具列表里有 a2a”：

```text
Manager派活 → Worker真改了文件 → 返回结构化报告 → Manager真去查了文件和测试 → 不行就打回重做 → 行才进入下一步
```

---

## 1. 总文件规划（先建好，以后都不乱）

最终你要在 `E:\Demo` 下得到这个结构：

```text
E:\Demo\
  Temp\                       # 你现在的位置，别动
  hermes-team\                # 本项目根目录，以后所有东西都在这里
    docs\                     # 需求母文档放这里
    configs\
      workers.yaml            # Worker注册表
      manager-prompt.md       # Manager人设+规则
    workers\
      echo-worker.py          # 最简Worker，用于打通闭环
      frontend-worker.py      # 第二阶段复制用
      backend-worker.py
    manager\
      task-schema.json        # 任务格式
      report-template.md      # Worker报告模板
      review-checklist.md     # Manager验收清单
    state\
      tasks.json              # 任务状态
      checkpoints\            # 断点恢复
    logs\
      a2a.log
      tasks.log
    tools\
      check-files.py          # Manager验收脚本：真查文件
      send-task.py            # 不用Hermes也能测试Worker的脚本
    test-project\             # 假项目，用来验证Worker真干活了
```

### S00：创建目录（原子级第1步）

目的：建好架子。

操作：打开 PowerShell，复制粘贴执行：

```powershell
# 1.确认你在E:\Demo
pwd
# 预期：E:\Demo 或 E:\Demo\Temp

# 2.创建结构
mkdir E:\Demo\hermes-team, E:\Demo\hermes-team\docs, E:\Demo\hermes-team\configs, E:\Demo\hermes-team\workers, E:\Demo\hermes-team\manager, E:\Demo\hermes-team\state\checkpoints, E:\Demo\hermes-team\logs, E:\Demo\hermes-team\tools, E:\Demo\hermes-team\test-project -Force
ls E:\Demo\hermes-team
```

预期：`ls` 能看到 7 个文件夹。看不到就是路径打错，重跑一次。

---

## 2. S01-S10：环境摸底（必须做，否则后面全是玄学）

你是小白，这 10 步是“体检”，每步 1 分钟。

### S01：验证 Hermes / Python / Node

```powershell
hermes --version
python --version
node --version
pip --version
```

预期：

```text
Hermes Agent v0.21.1
Python: 3.11.x
node: v18以上或v20以上
```

失败怎么办：`python --version` 没反应 → 去 Microsoft Store 装 Python 3.11，`node --version` 没反应 → 去 nodejs.org 装 LTS，装完关掉 PowerShell 重开再测。

### S02：找到 Hermes 家目录和配置

```powershell
Test-Path C:\Users\EDY\AppData\Local\hermes\config.yaml
Get-Content C:\Users\EDY\AppData\Local\hermes\config.yaml
ls C:\Users\EDY\AppData\Local\hermes\hermes-agent
```

预期：第一条返回 `True`，第二条打印出 yaml 内容，拍照保存。第三条能看到很多文件。

把 `config.yaml` 完整复制一份备份：

```powershell
Copy-Item C:\Users\EDY\AppData\Local\hermes\config.yaml E:\Demo\hermes-team\configs\config.backup-2026-09-11.yaml
```

### S03：看懂 A2A 插件真面目

```powershell
ls C:\Users\EDY\AppData\Local\hermes\hermes-agent\plugins\platforms\a2a
Get-Content C:\Users\EDY\AppData\Local\hermes\hermes-agent\plugins\platforms\a2a\plugin.yaml
Get-Content C:\Users\EDY\AppData\Local\hermes\hermes-agent\plugins\platforms\a2a\README.md
```

预期：能看到你需求文档 §47 说的 6 个文件：`adapter.py, protocol.py, security.py, tools.py, plugin.yaml, README.md`。

关键动作：打开 `DESIGN.md` 和 `tools.py` 只看两件事并记下来：

1. `a2a_discover / a2a_call / a2a_list / a2a_history / a2a_orchestrate` 每个函数的参数名是什么
2. `Agent Card` 的 URL 是不是 `/.well-known/agent.json`

命令：

```powershell
Select-String -Path C:\Users\EDY\AppData\Local\hermes\hermes-agent\plugins\platforms\a2a\*.py -Pattern "def |agent-card|well-known|endpoint|discover|call" | Select-Object -First 60
```

把输出保存：

```powershell
Select-String -Path C:\Users\EDY\AppData\Local\hermes\hermes-agent\plugins\platforms\a2a\*.py -Pattern "def |agent-card|well-known|endpoint|discover|call" | Out-File E:\Demo\hermes-team\logs\a2a-plugin-scan.txt
```

### S04：看 Hermes 有哪些命令

```powershell
hermes --help
hermes gateway --help
hermes agent --help
hermes tools --help
```

预期：能看到子命令列表。把它们存下来：

```powershell
hermes --help | Out-File E:\Demo\hermes-team\logs\hermes-help.txt
```

如果 `hermes tools --help` 报错，换成 `hermes tool --help` 或 `hermes mcp --help`，不纠结，记下来能用的那个。

### S05：检查 9900 端口（A2A Gateway）

```powershell
netstat -ano | Select-String "9900"
Test-NetConnection -ComputerName 127.0.0.1 -Port 9900
```

预期有两种都算正常：

- `Test-NetConnection` 显示 `TcpTestSucceeded: True` = Gateway 已在跑
- 显示 `False` = Gateway 没跑，后面我们会启动它

### S06-S07：大坑预警（需求 §48，必须遵守）

打开你的 `config.yaml`，检查有没有这一段：

```yaml
platform_toolsets:
  cli:
    - a2a
```

**如果有，删掉它或注释掉。** `a2a` 是插件，不是静态 builtin toolset，写在这里会导致启动报 `Unknown toolsets: a2a`。

正确的 A2A 启用条件是三选一（满足一个就行）：

```yaml
# 方式1：推荐，最直白
platforms:
  a2a:
    enabled: true
    port: 9900

# 方式2：声明远端Worker
a2a_agents:
  - http://localhost:8101
  - http://localhost:8102

# 方式3：环境变量
# $env:A2A_PORT="9900"
```

操作：先不要改配置，看完 S10 再统一改。

---

## 3. Phase 1：最小闭环 MVP（最重要，2-3小时）

> 对应需求 §41：`Manager启动→Worker启动→Discover→获能力→Call→执行→返回→Manager拿到结果`
> 策略：不用一上来就搞 4 个 Worker，先用 1 个 `Echo-Worker`（只用 Python 标准库，零依赖）打通。

架构：

```text
Hermes-Manager (9900)
   │ A2A http://localhost:8101
   ▼
Echo-Worker (8101, Python标准库)
   │ 真写文件到 E:\Demo\hermes-team\test-project\hello.txt
   ▼
返回JSON报告
```

### S11：创建 Echo-Worker（复制粘贴即可）

在 `E:\Demo\hermes-team\workers\echo-worker.py` 写入以下内容：

```python
# echo-worker.py - 零依赖最小Worker，只用Python标准库
# 功能: 1) GET /.well-known/agent.json 返回Agent Card
#       2) POST /tasks 执行任务并真写文件
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from datetime import datetime

PORT = 8101
WORK_DIR = Path(r"E:\Demo\hermes-team\test-project")
WORK_DIR.mkdir(parents=True, exist_ok=True)

AGENT_CARD = {
    "name": "echo-worker",
    "id": "echo-001",
    "description": "最小验证Worker，能写文件并返回结构化报告",
    "capabilities": ["echo", "write_file", "test"],
    "skills": ["echo", "file_write"],
    "inputModes": ["application/json"],
    "outputModes": ["application/json"],
    "endpoint": f"http://localhost:{PORT}/tasks",
    "taskTypes": ["echo", "write_file"],
    "auth": "none-for-local-dev"
}

class Handler(BaseHTTPRequestHandler):
    def _send(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/.well-known/agent.json", "/agent.json", "/card"):
            self._send(AGENT_CARD)
        elif self.path in ("/", "/health"):
            self._send({"status": "ONLINE", "worker": "echo-worker", "port": PORT})
        else:
            self._send({"error": "not found"}, 404)

    def do_POST(self):
        if self.path not in ("/tasks", "/a2a/tasks", "/call"):
            self._send({"error": "not found"}, 404)
            return
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8", errors="ignore") if length else "{}"
        try:
            task = json.loads(raw) if raw else {}
        except Exception:
            task = {"raw": raw}
        task_id = task.get("id", f"task-{datetime.now().strftime('%H%M%S')}")
        objective = task.get("objective", task.get("text", "echo test"))
        filename = task.get("input", {}).get("filename", "hello.txt") if isinstance(task.get("input"), dict) else "hello.txt"
        content = task.get("input", {}).get("content", f"hello from echo-worker at {datetime.now().isoformat()}") if isinstance(task.get("input"), dict) else str(objective)
        target = WORK_DIR / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        result = {
            "task_id": task_id,
            "status": "SUBMITTED",
            "objective": objective,
            "steps": [f"1.收到任务 {task_id}", f"2.写入文件 {str(target)}", "3.自测文件存在且非空"],
            "files_changed": [str(target)],
            "tests": [{"name": "file_exists_and_nonempty", "passed": target.exists() and target.stat().st_size > 0}],
            "evidence": {"file": str(target), "size": target.stat().st_size},
            "known_issues": [],
            "worker": "echo-worker/echo-001"
        }
        self._send(result)

    def log_message(self, *a):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {a[1] if len(a)>1 else a}")

if __name__ == "__main__":
    print(f"Echo-Worker on http://localhost:{PORT}")
    print(f"Card: http://localhost:{PORT}/.well-known/agent.json")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
```

PowerShell 快速创建（如果你不想手动建文件）：

```powershell
# 先确认文件已存在，上面内容已帮你规划好，直接用记事本粘贴最稳
notepad E:\Demo\hermes-team\workers\echo-worker.py
```

### S12：启动 Worker 并验证（不经过 Hermes，先证明 Worker 自己是好的）

开一个 PowerShell 窗口 A：

```powershell
python E:\Demo\hermes-team\workers\echo-worker.py
```

预期：打印 `Echo-Worker on http://localhost:8101`，窗口不要关。

再开一个新 PowerShell 窗口 B，执行三连验证：

```powershell
# 1.健康检查
Invoke-RestMethod http://localhost:8101/health | ConvertTo-Json

# 2.Agent Card（对应需求§5.1）
Invoke-RestMethod http://localhost:8101/.well-known/agent.json | ConvertTo-Json -Depth 5

# 3.派一个真任务（对应需求§11）
$body = @{ id="t-001"; objective="写一个hello文件"; input=@{ filename="hello.txt"; content="hi manager, worker ok" } } | ConvertTo-Json -Depth 5
Invoke-RestMethod -Method Post -Uri http://localhost:8101/tasks -Body $body -ContentType "application/json" | ConvertTo-Json -Depth 6

# 4.验文件真写进去了吗（对应需求§13 Manager必须真查）
Get-Content E:\Demo\hermes-team\test-project\hello.txt
```

全部通过标准：

- 第1步返回 `ONLINE`
- 第2步有 `name, id, capabilities, endpoint`
- 第3步返回 `SUBMITTED` 且 `tests.passed=true`
- 第4步能看到文件内容

任何一步失败：Worker 窗口 A 看报错，99% 是端口被占 → `netstat -ano | Select-String "8101"` 找到 PID 去任务管理器杀掉，重跑。

### S13：配置 Hermes Manager 端（只改一次）

1. 打开配置备份对比：

```powershell
notepad C:\Users\EDY\AppData\Local\hermes\config.yaml
```

2. 确保包含以下最小段（如果文件里已有 `platforms` 段就合并，不要重复）：

```yaml
platforms:
  a2a:
    enabled: true
    port: 9900
    allow_local: true

a2a_agents:
  - http://localhost:8101
```

3. 确保**没有** `platform_toolsets.cli: [a2a]`（见 S06）。

4. 重启 Hermes Gateway（两个命令二选一，哪个能用用哪个）：

```powershell
hermes gateway restart
# 或
hermes gateway start --port 9900
```

验证：

```powershell
Test-NetConnection -ComputerName 127.0.0.1 -Port 9900
hermes tools list | Select-String "a2a"
```

预期：端口 `True`，工具列表里出现 `a2a_discover, a2a_call, a2a_list`。如果没出现，把 `E:\Demo\hermes-team\logs\a2a-plugin-scan.txt` 和 `config.yaml` 发给 AI 排查，不要往下走。

### S14：Manager 通过 A2A 发现并调用（闭环封口）

在 Hermes 对话里（`hermes chat` 或你的 Gateway UI）依次输入这三句，每句都要成功：

```text
1. 用a2a_discover发现 http://localhost:8101，并显示它的Agent Card
2. 用a2a_call给它发任务：{id:"t-002", objective:"写verify.txt", input:{filename:"verify.txt", content:"manager via a2a"}} 
3. 收到结果后，读取 E:\Demo\hermes-team\test-project\verify.txt 并告诉我文件大小
```

判定 Phase 1 成功（对应 §46）：

- [ ] `a2a_discover` 返回了 echo-worker 的 Card
- [ ] `a2a_call` 返回了 `SUBMITTED` 结构化报告
- [ ] Manager 自己去读了 `verify.txt` 而不是只说“完成了”
- [ ] `E:\Demo\hermes-team\test-project\` 下真有两个文件

这时你已经证明了 §41 的 8 步闭环。停下来庆祝，Phase 1 结束。

---

## 4. Phase 2：Registry + 多 Worker + 并行（第 2 天）

### S20：创建 Worker 注册表

`E:\Demo\hermes-team\configs\workers.yaml`：

```yaml
workers:
  - id: echo-001
    name: Echo Worker
    role: connectivity-test
    endpoint: http://localhost:8101
    protocol: a2a
    enabled: true
    skills: [echo, file_write]

  - id: frontend-001
    name: Frontend Developer
    role: Frontend Development
    endpoint: http://localhost:8102
    protocol: a2a
    enabled: false   # 第二阶段再打开
    skills: [frontend, html, css]

  - id: backend-001
    name: Backend Developer
    role: Backend Development
    endpoint: http://localhost:8103
    protocol: a2a
    enabled: false
    skills: [backend, api]
```

验证：

```powershell
Get-Content E:\Demo\hermes-team\configs\workers.yaml
python -c "import yaml,sys; yaml.safe_load(open(r'E:\Demo\hermes-team\configs\workers.yaml')); print('yaml ok')"
# 如果缺yaml库：pip install pyyaml
```

### S21：复制出 frontend/backend Worker

```powershell
Copy-Item E:\Demo\hermes-team\workers\echo-worker.py E:\Demo\hermes-team\workers\frontend-worker.py
Copy-Item E:\Demo\hermes-team\workers\echo-worker.py E:\Demo\hermes-team\workers\backend-worker.py
```

用记事本打开两个复制文件，只改两处：`PORT = 8102 / 8103`，`AGENT_CARD["name"]` 改成对应名字。启动三个窗口分别运行，验证三个端口都 `ONLINE`。然后把 `workers.yaml` 里那两个 `enabled: false` 改成 `true`，并在 `config.yaml` 的 `a2a_agents` 里加上 8102、8103，重启 gateway。

并行验证任务（对应需求 §20）：

```text
在Manager里说：同时给8101、8102、8103各发一个写文件任务，文件名分别是p1.txt/p2.txt/p3.txt，然后同时汇报三个结果
```

预期：三个文件几乎同时出现，时间差 < 5 秒。证明并行。

---

## 5. Phase 3：任务 + 报告 + 验收 + 返工（核心，第 3-4 天）

### S30：固定三份模板（以后 Manager/Worker 都用它，不许自由发挥）

`E:\Demo\hermes-team\manager\task-schema.json`（对应 §11）：

```json
{
  "id": "FE-001",
  "project_id": "demo-shop",
  "phase_id": "phase-3-frontend",
  "role": "frontend",
  "objective": "创建首页 index.html",
  "requirements": ["纯静态", "中文", "有标题和按钮"],
  "constraints": ["只改 test-project 目录", "不联网下载"],
  "input": {"filename": "index.html"},
  "expected_output": "test-project/index.html 存在且可打开",
  "acceptance_criteria": ["文件存在", "包含<h1>", "包含<button>"],
  "dependencies": [],
  "priority": "P0"
}
```

`E:\Demo\hermes-team\manager\report-template.md`（对应 §12）：Worker 必须按这 13 项回，否则 Manager 打回。

```text
1.任务目标 / 2.执行过程 / 3.修改了什么 / 4.文件列表 / 5.核心代码 diff / 6.用了哪些工具 / 7.执行了哪些测试 / 8.测试结果 / 9.当前状态 / 10.已知问题 / 11.风险 / 12.验收证据(文件路径+大小+截图) / 13.后续建议
```

`E:\Demo\hermes-team\manager\review-checklist.md`（对应 §13-§15）：

```text
- [ ] 文件真存在？跑 tools\check-files.py
- [ ] 内容满足 acceptance_criteria？
- [ ] 测试全绿？
- [ ] 没改不该改的文件？git status 看
- 状态机：PENDING→ASSIGNED→RUNNING→SUBMITTED→REVIEWING→ APPROVED/COMPLETED 或 REJECTED→REWORK→RUNNING
- REJECT必须带：原因+证据+修复任务单（新的task id）
```

验收脚本 `E:\Demo\hermes-team\tools\check-files.py`：

```python
import sys, pathlib
base = pathlib.Path(r"E:\Demo\hermes-team\test-project")
need = sys.argv[1:] or ["hello.txt"]
ok = True
for f in need:
    p = base / f
    print(f"{'OK' if p.exists() and p.stat().st_size>0 else 'FAIL'} {p} size={p.stat().st_size if p.exists() else 0}")
    ok &= p.exists() and p.stat().st_size > 0
sys.exit(0 if ok else 1)
```

验证：

```powershell
python E:\Demo\hermes-team\tools\check-files.py hello.txt verify.txt
echo $LASTEXITCODE
# 预期 0，有一个不存在就非0，Manager看到非0就必须REJECT
```

返工闭环话术（Manager 必须这么做，对应 §14）：

```text
Worker说Done → Manager跑check-files.py → FAIL → 生成新任务 FE-001-R1（写明缺了<button>）→ a2a_call重派 → Worker重交 → 再验 → 通过才COMPLETED
```

做一次故意失败演练：让 Worker 写一个不带 `<button>` 的 `index.html`，看 Manager 能否发现并打回。能打回，Phase 3 才算过。

---

## 6. Phase 4：长期运行 + 人工确认 + 日志（第 5 天）

一次只加三件小事，不要贪多：

1. **Checkpoint（对应 §19/§31）：** 每次派活前，把 `task json` 追加到 `state/tasks.json`，电脑重启也不丢。

```powershell
# 手动验证一次就行
Copy-Item E:\Demo\hermes-team\manager\task-schema.json E:\Demo\hermes-team\state\checkpoints\chk-001.json
ls E:\Demo\hermes-team\state\checkpoints\
```

2. **两种模式（对应 §18）：** 在跟 Manager 说话时加一句话切换：
   - 全自动：`Full Auto模式：不要问我，自动派活、验收、返工，直到PROJECT_COMPLETED`
   - 逐步确认：`Step模式：做完一步就停下，给我看报告和证据，等我说resume才继续`

3. **日志（对应 §32）：** 所有 `a2a_call` 结果都 `Out-File -Append logs/a2a.log`。Web UI（§33）先不做，用文件夹+记事本看，Phase 5 再做。

高风险拦截（对应 §17 HITL）：Manager prompt 里加死规则：`删文件、删库、git push --force、发布生产、改Hermes配置，必须先SUSPEND等用户说批准`。

`E:\Demo\hermes-team\configs\manager-prompt.md` 第一版一句话就够：

```text
你是Hermes-Manager，唯一调度者。你不直接写所有代码，只分活、验收、打回。
每次收到Worker的Done，必须先跑check-files.py看文件、看测试证据，不通过就REJECT并发修复任务。
任务格式用manager/task-schema.json，报告必须含13项，否则打回。
```

---

## 7. Phase 5：扩成真团队（以后）

当前 4 角色够用（对应 §10）：`UI Designer(8101) / Frontend(8102) / Backend(8103) / Data集成(8104)`。后面再加 `QA / Reviewer / DevOps`，每个都是复制 `echo-worker.py` 改端口+改 `skills`，注册到 `workers.yaml` 即可。

Git 隔离（对应 §22），现在就可以用：

```powershell
cd E:\Demo\hermes-team\test-project
git init; git add .; git commit -m "init"
git checkout -b task/FE-001
# Worker只在这个分支改，Manager验收通过才 merge 到 main
```

模型/工具可配置（对应 §35-§36）：不要写死在代码里，以后把 `Manager用gpt-x，Worker用claude-y` 写进 `configs/models.yaml`，Tool 开关写进 `workers.yaml` 的 `tools: [file, terminal, browser]` 字段即可。现在知道有这个位置就行，不用实现。

---

## 8. 每日验证总表（经得起验证的关键）

| 阶段 | 验证命令 | 通过标准 |
|---|---|---|
| Phase1 | `Invoke-RestMethod http://localhost:8101/.well-known/agent.json` + Hermes里 `a2a_discover/a2a_call` | 文件真生成，Manager真读文件 |
| Phase2 | 三个端口 `/health` 全 ONLINE + `p1/p2/p3.txt` 同时生成 | 并行 <5s |
| Phase3 | `python tools\check-files.py index.html; echo $LASTEXITCODE` | 缺 `<button>` 时必须 REJECT 并重派 |
| Phase4 | 重启电脑后 `ls state\checkpoints\` 还在 | 能 resume |
| 全流程 | 从“做个首页”到 `PROJECT_COMPLETED` 无人值守跑完 | 日志里有完整 `ASSIGNED→RUNNING→SUBMITTED→REVIEWING→APPROVED` 链 |

故障速查：

- `Unknown toolsets: a2a` → 删 `platform_toolsets.cli` 里的 `a2a`
- `a2a工具看不到` → 检查 `platforms.a2a.enabled / a2a_agents / A2A_PORT` 三选一是否满足，重启 gateway
- `连不上8101` → Worker 窗口没开 / 防火墙弹框点允许 / `netstat -ano` 查占用
- `Worker说Done但文件没有` → 永远信文件不信话，直接 REJECT

---

### 你现在要做的下一步（只做一步）

1. 执行 S00+S01+S02，把 `config.yaml` 内容和 `hermes --help` 输出贴回来。
2. 我帮你核对后再给你 S11 的启动确认。不要跳步，一步一验，闭环先行。

这套方案严格对应你的母文档 §41→§45 的五阶段，先让 `Manager→A2A→Worker→Result→Review→Rework` 真转起来，再谈 Web UI 和 AI 公司。
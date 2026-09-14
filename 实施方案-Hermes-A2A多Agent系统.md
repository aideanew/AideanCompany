# Hermes 多 Agent 全自动开发系统 · 实施方案 v2（已部署 + 实测通过）

| 项 | 内容 |
|---|---|
| 版本 | v2（2026-09-12，最小闭环已在真机测试通过） |
| 上位文档 | 《Hermes 多 Agent 全自动开发系统》总需求母文档；`docs/管理员全局设定示例.txt`；`docs/任务提交给管理员示例.txt` |
| 核心参考 | `Claude5.1完成规划.md`（已逐行审读，其可取部分已吸收，致命缺陷已修正，见 §9） |
| 测试证据 | [fleet/reports/loop-test-20260912.md](fleet/reports/loop-test-20260912.md) |
| 适用对象 | 零基础用户；任何新项目都可直接复用本流程（见 §6） |

---

## 0. 当前状态（本方案已全部落地并测试通过）

| 组件 | 状态 |
|---|---|
| Manager（Hermes-Manager，端口 9900；**测试用模型 agnes-3.0-flash**，正式运行可切回 gpt-6-astra） | ✅ 已配置，网关运行中 |
| Worker-A/B/C（端口 9901/9902/9903；SenseNova / b.ai+代理 / ModelScope，替补 NVIDIA，详见 §2 模型矩阵） | ✅ 已创建并连通 |
| A2A 出站工具（a2a_list/discover/call/history/orchestrate） | ✅ 已启用并实测 |
| 最小闭环（派工→真干活→报告→独立审查→总表） | ✅ PASS（含 429 退避恢复、PARTIAL→补充证据→PASS 审查闭环） |

**日常启动**：双击运行 `fleet\start-fleet.ps1`（4 个网关）。
**日常使用**：`hermes --yolo chat` 跟经理说话，下达项目目标即可。

---

## 1. 三轮推理的最终架构结论（含前提与局限）

```text
                 你（老板）
                    │ hermes --yolo chat
                    ▼
         ┌─────────────────────┐
         │  Hermes-Manager     │  端口 9900 · 测试模型 agnes-3.0-flash（正式切回 gpt-6-astra）
         │  SOUL=管理者章程      │  拆解/派工/独立审查/返工/总表
         └──────────┬──────────┘
                    │ A2A v1.0 JSON-RPC（a2a_call）
      ┌─────────────┼─────────────┐
      ▼             ▼             ▼
 Worker-A       Worker-B      Worker-C     ← Hermes profile ×3
 员工A 前端/UI   员工B 后端     员工C 测试联调
 9901           9902          9903         ← 廉价模型（ModelScope DeepSeek Flash）
      └─────────────┼─────────────┘
                    ▼
        E:\Code\AideanCompany\fleet\projects\<项目名>\
        （真实文件交付物 + reports\ 验收报告）
```

**为什么是 Hermes profile 当 Worker，而不是 Claude5.1 规划里的自研 echo-worker：**
echo-worker 只会讲"自定义协议"（POST /tasks + agent.json），而 Hermes 的 `a2a_call` 说的是 **A2A v1.0 JSON-RPC**（`message/send` + `/.well-known/agent-card.json`）。两者不兼容——照抄会导致 Manager 永远调不通 Worker。Hermes profile 原生就是标准 A2A 服务端，且模型/密钥/人设/端口完全独立，"再招一个员工"= 一条命令。**echo-worker 阶段可以跳过，直接从 profile 员工起步**（本次实测正是如此）。

**采用 Claude5.1 规划的部分**：舰队目录结构、任务包模式（task schema）、`执行就绪总表`、Full-Auto/Step 双模式、高危动作人工拦截（HITL）、每日验证总表、故障速查表。
**舍弃并修正的部分**：echo-worker（协议不兼容）、`a2a_agents` 写成 URL 列表（插件实际要求 `名字: {url, timeout, capabilities}` 映射）、`platforms.a2a.port` 顶层写法（入站端口实际在 `gateway.platforms.a2a.extra.port`）。

**前提与局限**：
- 前提1：各网关进程在运行（关窗=员工下线）。
- 前提2：ModelScope 免费档有每分钟 token 限制，Worker 系统提示词必须保持精瘦（skills 已移出，勿再往 worker profile 灌大技能包）；并发派工遇 429 属正常，退避重试。
- 局限1：Flash 级模型偶尔输出瑕疵（如报告表格漏填文件名），这正是"机器验收"存在的意义——审查环节会拦住。
- 局限2：本机单机、127.0.0.1 明文无令牌，仅适合本机演练；跨机器组队前必须按 §8 加令牌。
- 局限3：`hermes doctor` 提示 config 版本 v25→v42 可迁移（warn-only），暂不迁移，避免动已验证的配置。

---

## 2. 已部署配置的精确位置（改配置时只动这些地方）

| 内容 | 路径 |
|---|---|
| Manager 配置 | `C:\Users\EDY\AppData\Local\hermes\config.yaml`（备份：`fleet\configs\config.manager.bak-20260912.yaml`） |
| Manager 人设（管理者章程） | `C:\Users\EDY\AppData\Local\hermes\SOUL.md`（备份：`fleet\configs\SOUL.manager.bak.md`；现行版：`fleet\configs\manager-SOUL.md`） |
| Manager 名字 | `.env` 里 `A2A_AGENT_NAME=Hermes-Manager` |
| Worker 配置 | `C:\Users\EDY\AppData\Local\hermes\profiles\worker-a|b|c\config.yaml` |
| Worker 人设（员工守则） | `profiles\worker-x\SOUL.md`（模板：`fleet\configs\worker-SOUL-template.md`） |
| Worker 模型/密钥/名字 | profile 的 `config.yaml` model 块 + `.env`（`HERMES_CUSTOM_API_MODELSCOPE_API_KEY`、`A2A_AGENT_NAME`） |
| Worker 通讯录（Manager 侧） | Manager config 末尾 `a2a_agents:` 映射 |
| 被移出的 Worker 技能包 | `fleet\configs\skills-backup-worker-x\skills\`（要恢复就移回 profile 目录） |
| 配置脚本（可重跑，幂等） | `fleet\tools\setup_cfg.py`、`setup_env.py`、`setup_souls.py`、`setup_manager.py` |

**Manager config 中的两段关键配置（现状即如此，勿改格式）：**
```yaml
gateway:
  strict: false
  platforms:
    a2a:
      enabled: true
      extra:
        port: 9900        # 入站 Agent Card 服务
  media_delivery_allow_dirs: []
  ...
```
```yaml
# 文件末尾
a2a_agents:
  worker-a:
    url: "http://127.0.0.1:9901"
    timeout: 600
    capabilities: [ui_design, general]
  worker-b:
    url: "http://127.0.0.1:9902"
    timeout: 600
    capabilities: [backend, general]
  worker-c:
    url: "http://127.0.0.1:9903"
    timeout: 600
    capabilities: [testing, general]
```
**Worker 模型矩阵（2026-09-12 v3 接线，脚本 fleet\tools\setup_models_v3.py 幂等可重跑）：**

| 角色 | 端点 | 模型 | 备注 |
|---|---|---|---|
| worker-a 前端 | https://token.sensenova.cn/v1 | sensenova-6.8-flash-lite | 直连 |
| worker-b 后端 | https://api.b.ai/v1 | qwen3.8-flash | **必须 http://127.0.0.1:10808 代理**（.env 注入 HTTP(S)_PROXY + NO_PROXY=127.0.0.1,localhost） |
| worker-c 测试 | https://api-inference.modelscope.cn/v1 | deepseek-ai/DeepSeek-V4-Flash-0731 | 免费档，串行+退避 |
| 全员替补 | https://integrate.api.nvidia.com/v1 | nvidia/nemotron-3-ultra-550b-a55b | 已写入各 Worker `fallback_providers`（key_env 走 .env） |

示例（worker-a 的 config.yaml 模型块；b/c 同结构不同值）：
```yaml
model:
  default: sensenova-6.8-flash-lite
  provider: custom
  base_url: https://token.sensenova.cn/v1
  api_key: ${HERMES_CUSTOM_API_SENSENOVA_API_KEY}
  api_mode: chat_completions
```
密钥一律在 profile `.env`（`HERMES_CUSTOM_API_SENSENOVA_API_KEY` / `HERMES_CUSTOM_API_BAI_API_KEY` / `HERMES_CUSTOM_API_MODELSCOPE_API_KEY` / `HERMES_CUSTOM_API_NVIDIA_API_KEY`）。

**Manager 模型块（测试版，2026-09-12 起生效）：**
```yaml
model:
  default: agnes-3.0-flash
  provider: custom
  base_url: https://apihub.agnes-ai.com/v1
  api_key: ${HERMES_CUSTOM_API_AGNES_API_KEY}
  api_mode: chat_completions
```
密钥在 Manager `.env` 的 `HERMES_CUSTOM_API_AGNES_API_KEY`。**切回正式模型**只需改回三行：`default: gpt-6-astra`、`base_url: https://api.gpt.ge/v1`、`api_key: ${HERMES_CUSTOM_API_GPT_GE_API_KEY}`，然后 `hermes gateway restart`。切换前备份：`fleet\configs\config.manager.bak-before-agnes.yaml`。

---

## 3. A2A 工具生效的 4 个条件（本次实测总结，缺一不可）

1. config.yaml 里有 `a2a_agents`（通讯录）；
2. 或环境变量 `A2A_PORT`、或顶层 `platforms.a2a.enabled`；
3. **工具注册表开关**：`hermes tools enable a2a`（新发现——工具列表里 a2a 显示 ✗ disabled 时，`hermes -z` 会报"工具未加载"）；
4. **绝不**把 a2a 写进 `platform_toolsets`（会报 Unknown toolsets: a2a）。

排查看工具是否可用：`hermes tools list | findstr a2a` 应显示 `✓ enabled`。

---

## 4. 给任何项目用的标准流程（本方案的核心复用价值）

对任何新项目（不限 E:\Code\AideanCompany），流程固定六步：

### 第 1 步：准备项目文档（10 分钟，人的工作）
在项目目录放好：目标说明（要做什么）、约束（端口/禁区）、验收标准（可执行命令）。没有文档就先让 Manager 帮你把想法整理成文档（这是它唯一亲自写的"代码"）。

### 第 2 步：启动舰队
双击 `fleet\start-fleet.ps1`。验证：`curl.exe http://127.0.0.1:9900/.well-known/agent-card.json` 返回 Hermes-Manager。

### 第 3 步：下达目标（一次交代，不问答）
```powershell
hermes --yolo chat
```
对经理说（示例模板）：
```text
项目代号 <名字>。目标：<一句话>。
工作目录：E:\Code\AideanCompany\fleet\projects\<名字>（或你的真实项目目录）。
拆解要求：
- 任务给谁（worker-a 前端/UI / worker-b 后端 / worker-c 测试）你按职责定；
- 可并行的并行，有依赖的等依赖；
- 每个任务包包含：编号/目标/工作目录/允许与禁止改动范围/要产出的文件/验收命令清单；
- 全部完成后你亲自跑验收命令，判定 PASS/PARTIAL/REWORK/BLOCKED，
  REWORK 就带证据派返工包，最后写报告到 fleet\reports\<名字>-<日期>.md 并给我执行就绪总表。
铁律：<端口/禁区等硬约束>。
```

### 第 4 步：观察与放行（两种模式，随口切换）
- `Full Auto模式：不要问我，自动派活、验收、返工，直到全部完成`
- `Step模式：每完成一个任务就停下来，给我看报告和证据，等我说继续`

### 第 5 步：你只看两样东西
1. `fleet\reports\<项目>-<日期>.md`（六节报告）；
2. 执行就绪总表里有没有 `ESCALATED`/`BLOCKED`（有才需要你介入）。

### 第 6 步：收尾
关闭 4 个网关窗口（或 `hermes gateway stop`）。项目文件和报告永久留在 fleet\ 里。

---

## 5. Manager 与 Worker 的人设（已按你的两份参考文件定制）

- **Manager 章程**（`fleet\configs\manager-SOUL.md`，已生效）：融合《管理员全局设定示例》的验收顺序八步、判定三态、证据链表格式，与《任务提交给管理员示例》的 PASS/PARTIAL/REWORK/BLOCKED 审查循环、执行就绪总表、"一个工作包 BLOCKED ≠ 员工整体 BLOCKED"原则、无依赖不停工原则；外加 A2A 派工细则（任务包格式、返工上限 3 次、ESCALATED 上报）。
- **Worker 守则**（`fleet\configs\worker-SOUL-template.md`，三个 profile 已各自实例化）：融合员工铁律（不扩范围/零反问/证据链/不伪造测试/BLOCKED 上报）+ 四轮深度分析法（5W1H 精简版）+ 六节报告格式（结论四选一/执行过程/改动清单/验证记录/证据链/未完成事项）。
- **MCP/skills 决策**：MVP 不接 MCP（文件与终端工具已内置够用）；Worker 不挂 skills（免费档 TPM 限制，且守则已内置方法论）。Manager 保留默认技能。

---

## 6. 故障排查表（v2，含 9-12 实测新增项）

| 症状 | 原因 | 处理 |
|---|---|---|
| `hermes -z` 说"a2a 工具未加载" | 工具注册表被禁用 | `hermes tools enable a2a`，再 `hermes tools list` 确认 ✓ |
| Worker 报 429 insufficient_quota（#token-limit） | ModelScope 免费档 TPM/配额 | 等待 60s 退避重试；避免同时派发多个任务；保持 Worker 提示词精瘦 |
| 想换/查模型 | 模型 ID 必须以目录为准 | `curl.exe -H "Authorization: Bearer <key>" https://api-inference.modelscope.cn/v1/models` 查有效 ID（如 DeepSeek-V4.1-Flash 不存在，V4-Flash-0731 / V4-Pro 存在） |
| 网关启动报错退出 | config.yaml 缩进错 | 对照 §2 的配置块；或用 fleet\configs\ 里的备份覆盖 |
| 拿不到 Agent Card | 网关没起/端口不对 | `hermes gateway status`；`netstat -ano \| findstr :9900` |
| a2a_list 显示 no peers | a2a_agents 不在 config 顶层 | 对照 §2 末尾块 |
| 网关抢 9900 | profile 克隆后没改端口 | 改 profile config 的 `extra.port` |
| Worker 名字不对 | A2A_AGENT_NAME 未生效 | 查 profile `.env`，重启网关 |
| Worker 回复 [INPUT_REQUIRED] | 任务包信息不足 | 补充信息继续对话；或完善任务包重派 |
| A2A 往返 5 轮被拒 | 防死循环 A2A_MAX_PINGPONG_TURNS=5 | 正常保护；新任务=新 a2a_call 上下文 |
| 上下文里看不到 a2a 工具 | 见 §3 四条件 | 逐条核对 |

---

## 7. 每日验证总表（沿用 Claude5.1 规划并实测修订）

| 阶段 | 验证命令 | 通过标准 |
|---|---|---|
| 舰队在线 | 4 个端口 curl agent-card | name 全部正确 |
| 通讯录 | `hermes --yolo -z "调用 a2a_list"` | 3 peers + caps |
| 能力发现 | `a2a_discover` 任一 Worker | 返回名片技能 |
| 真实派工 | a2a_call 发一个建文件任务 | 文件真实存在且内容匹配 |
| 独立审查 | Manager 亲自跑验收命令 | PASS/PARTIAL/REWORK 判定 + 总表 |
| 审计 | `Get-Content ~\AppData\Local\hermes\a2a_audit.jsonl -Tail 5` | 有完整调用记录 |

---

## 8. 下一步路线（按母文档阶段推进）

1. **阶段 5 完整版**：真实项目闭环（todo-station 或你的真实项目），含返工演练与假完成实验（步骤见 v1 文档存档思路：故意设一个当前不满足的验收标准，观察 REWORK 循环）。
2. **Git 隔离**：项目目录 `git init`，Worker 在 `task/<编号>` 分支干活，Manager 验收通过才 merge（对应需求文档 FR-7.1，无需写代码）。
3. **三基座接入**：Worker SOUL 追加"允许用终端调用 claude/codex/opencode"，让员工借力最强编码 CLI（ADR-003）。
4. **成本与预算**：升级 ModelScope 付费档或给 Manager 也配 fallback；在章程中加预算上限规则。
5. **多机组队**（跨机器才做）：Worker 机 `.env` 设 `A2A_PEER_TOKENS=manager:<长随机串>` + `A2A_HOST=0.0.0.0`；Manager 侧对应 peer 加 `auth: { type: bearer, token: <同一串> }`。
6. **开机自启**：`shell:startup` 放 start-fleet.ps1 快捷方式。

---

## 9. 与 Claude5.1 完成规划的逐项对照（审读结论）

| Claude5.1 规划条目 | v2 处置 | 理由 |
|---|---|---|
| S00 目录结构（hermes-team 七件套） | ✅ 采纳（演化为 fleet\ 六目录） | 结构清晰，报告/配置/脚本分置 |
| S01-S05 环境体检 | ✅ 采纳（v1 阶段 0 已含） | 事实核查先行 |
| S06-S07 大坑预警（platform_toolsets） | ✅ 采纳并实测确认 | 母文档 §48 正确 |
| S11-S12 自研 echo-worker | ❌ **舍弃** | 自定义协议与 Hermes a2a_call 的 JSON-RPC v1.0 不兼容；Agent Card 路径、任务提交格式全对不上。Hermes profile 直接就是合规 A2A 服务端 |
| S13 `a2a_agents: - url列表` 写法 | ❌ 修正 | 插件要求 `名字: {url, timeout, capabilities}` 映射，否则 a2a_call 按名解析失败 |
| S13 `platforms.a2a.port` | ⚠️ 修正 | 入站端口真实位置是 `gateway.platforms.a2a.extra.port`（源码 adapter.py L261） |
| S20-S22 workers.yaml 注册表 | ⚠️ 简化 | `a2a_agents` 本身就是注册表（含 capabilities），不再重复维护第二份 |
| S30 任务包/报告/验收三模板 | ✅ 采纳（升级） | 与两份参考 txt 的任务包/证据链/总表格式合并成 SOUL 章程，天然生效 |
| check-files.py 验收脚本 | ✅ 思想采纳 | Manager 用内置终端亲自验收（已实测），无需独立脚本；保留 `fleet\tools\` 位置 |
| 状态机 PENDING→…→APPROVED | ✅ 采纳 | 落在 Manager 章程的审查循环与总表里 |
| Phase4 Checkpoint/双模式/HITL/日志 | ✅ 采纳 | Full-Auto/Step 口头切换；高危动作拦截已写入章程；审计用 a2a_audit.jsonl（现成） |
| Phase5 四角色扩展/Git 隔离/模型可配置 | ✅ 采纳为路线 | 见 §8 |

---

## 10. 网页控制台（v1，已实测）

**启动**：右键 `fleet\console\start-console.ps1` → 使用 PowerShell 运行 → 浏览器开 `http://127.0.0.1:5000`（仅本机）。
**代码**：`fleet\console\console.py`（零依赖，纯 Python 标准库，~800 行）。**v2（9-12 晚）**：深色专业 UI 重构（ui-ux-pro-max 规范）、项目看板（进度加权%/整体耗时/ETA/按角色 token 估算，取自各角色 a2a_conversations 真实文本量÷2.6）、角色完整增删改查、职能名称自由填写（前端开发/营销/客服…）+ 流程权限固定三选一、"烟测"更名"连通测试"、删除角色二次确认且同步清理通讯录（CRUD 全循环已实测）。
**v2.1（9-12 深夜）**：基础舰队配置 = 1 产品经理(pm-1) + 2 前端(worker-a/fe-2) + 3 后端(worker-b/be-2/be-3) + 1 测试(worker-c)，七角色烟测全"就绪"；**职能提示词模板**四套（产品/前端/后端/测试，按职能关键词自动套用，含全员铁律+六节报告）；**通用基座配置**一键应用（保留 browser/web/file/terminal/memory/session_search，裁剪 computer_use/tts/video/discord 等 17 项重型工具集，控提示词体积防免费档 TPM）；**新项目一键脚手架** `fleet\tools\new-project.ps1`（目录+契约模板+git+注册项目看板）。
**Skills/MCP 现状**：Worker 端 skills 保持移除（实测 22KB 索引会打爆免费档 TPM，职能流程已内置在 SOUL）；MCP 未接入（按 ADR-011 边界，后续经 `hermes mcp` 按需挂载，不替代内部调度）。

### 四页功能
| 页 | 功能 |
|---|---|
| 总览 | 四条件自检（hermes/名片/a2a工具启用/审计）+ 角色在线状态 + 最近任务 |
| 角色 | 名册（类型/端口/模型/状态）；**网页直接加人**（自动建 profile+SOUL模板+端口+密钥+同步 Manager 通讯录）；每角色【启动/烟测/停止】；改模型（必须烟测通过才算 online） |
| 任务 | 任务板（状态机 DRAFT→ASSIGNED→DOING→SUBMITTED→REVIEWING→DONE/PARTIAL/REWORK/BLOCKED）；新建任务（执行者下拉只显示 worker、审查者只显示 reviewer）；派工（只经 Manager）→ 机器验收 → 送审 → 返工/收口 |
| 审计 | 每次流转：时间/谁/动作/任务/详情（JSONL 落盘） |

### 流程正确性靠六道门（对应你三轮推理幸存结论）
1. **类型化角色**：类型四选一；派工下拉只列 worker、送审只列 reviewer——权限由类型决定，不由名字决定。
2. **状态机硬门**：非法迁移服务端直接拒绝（如 SUBMITTED 不能跳 DONE）。
3. **机器门**：`grep:相对路径:令牌1,令牌2` 模式（Python 直读 UTF-8，避开 findstr 的 GBK 陷阱）或白名单命令；**退出码非 0 永远存不进 PASS**；证据文件落 `state\evidence\`。
4. **目录白名单**：工作目录必须在 E:\Demo 或 fleet\projects 内。
5. **命令黑名单**：taskkill/del/rm/format/reg 等 20+ 危险模式直接拒绝。
6. **派工只经 Manager**：网页→hermes -z→a2a_call→Worker，网页永不直调 Worker 执行任务。

### 实测结果（2026-09-12）
- ✅ 网页端创建 worker-d(9904, agnes) + reviewer-f(9905, ModelScope→后切 agnes)，烟测"就绪"全过，Manager 通讯录自动同步
- ✅ T-001 全生命周期走通并 DONE：网页建任务→经 Manager 派工→worker-d 真实交付 docs\player-guide.md（1418B，三节齐全）→机器验收 PASS→按升级原则人工收口
- ✅ 舰队健康 14/14；网关改为**脱离进程组启动**（控制台重启不再连带杀舰队——实测踩坑后修复）

### 已知问题（R0 修复后状态，2026-09-12 深夜复核）
1. ~~agnes 当 Manager 编排挂死~~ → **已缓解**：Manager config 的 MCP 全部移除（context7 死链/exa/chrome-devtools/sequential-thinking 迁至员工侧——员工干活时才有 MCP，Manager 派工零 MCP 负担），派工响应 35s→7.2s；剩余 7 秒是 agnes API 自身延迟，**要进 5s 内需换更快端点或 gpt-6**。
2. ~~Manager -z 空回执~~ → 已加重试；仍空则从 a2a_history/审计取回执。
3. **密钥卫生（已全面整改）**：apifree 辅助密钥(12处×8文件)→`${HERMES_CUSTOM_API_APIFREE_KEY1}`；exa Key 从 config 删除→进程环境继承（.env 注入，8 个 .env）；setup 脚本脱敏（原件 .bak 改名）；config bak 脱敏。roster/config 全线无明文。
4. **MCP 归属架构**：MCP 只挂员工侧（exa 联网 + sequential-thinking 推理，经 `hermes mcp test` 验证连通；context7 死链已从全员清除）；Manager 零 MCP。worker-b/be-2/be-3 的出网走 10808 代理。
5. **审查门**：常驻审查员 reviewer-1（9911，agnes）已重建并烟测通过，送审下拉可用；T-001 历史断链已加退役徽章与说明。
6. wmic 缺失的系统上【停止】按钮可能无效（手动关窗口即可）；总览页因要跑 hermes 子进程加载约 10 秒。

---

## 11. 回退方法

| 要回退的 | 方法 |
|---|---|
| Manager config | 用 `fleet\configs\config.manager.bak-20260912.yaml` 覆盖，`hermes gateway restart` |
| Manager 人设 | 用 `fleet\configs\SOUL.manager.bak.md` 覆盖 SOUL.md |
| 删除某员工 | 关其网关窗口 → `hermes profile delete worker-a` |
| 恢复 Worker 技能包 | 把 `fleet\configs\skills-backup-worker-x\skills` 移回 profile 目录 |
| 全部停止 | 关网关窗口；`hermes gateway stop`；紧急 `hermes pause` |

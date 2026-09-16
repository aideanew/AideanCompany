# -*- coding: utf-8 -*-
"""
AideanAgentFleet 控制台 v2 —— 零依赖（纯标准库）
============================================
v2 新增：
- 全新深色专业 UI（设计令牌按 ui-ux-pro-max 规范：SVG图标/状态徽章/4.5:1对比度/hover无位移）
- 项目层：整体耗时、进度%、预计剩余与预计完成时间、按角色的 token 消耗估算（源自 a2a_conversations 真实数据量）
- 角色完整增删改查：职能名称自由填写（前端开发/营销/客服…），流程权限固定四选一保证流程正确性
- 连通测试（烟测）改名+说明；删除角色需二次确认
正确性六道门不变：类型化流程权限 / 状态机硬门 / 机器门(退出码判定) / 目录白名单 / 命令黑名单 / 派工只经 Manager
"""
import json
import os
import importlib
import importlib.util
import re
import shutil
import socket
import subprocess
import threading
import time
import urllib.request
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

FLEET = Path(r"E:\Code\AideanCompany\fleet")
STATE = FLEET / "console" / "state"
SOULS = STATE / "souls"
EVIDENCE = STATE / "evidence"
LOGS = FLEET / "console" / "logs"
for d in (STATE, SOULS, EVIDENCE, LOGS):
    d.mkdir(parents=True, exist_ok=True)

ROSTER_FILE = STATE / "roster.json"
TASKS_FILE = STATE / "tasks.json"
PROJECTS_FILE = STATE / "projects.json"
AUDIT_FILE = STATE / "audit.log"
STATIC_DIR = FLEET / "console" / "static"     # G1：/static/* 静态资源根（前端 plan-sync-client.js）
STREAM_HEARTBEAT_SEC = 15                     # G2：/api/stream 无事件时的 SSE 心跳间隔
CONSOLE_VERSION = "3.1.0-launchbus"           # v3：通用启动器事件总线+BOOT解析；/api/health 自带此版本号，未见即旧进程
FLEET_API_TOKEN = os.environ.get("FLEET_API_TOKEN", "")  # R6：写操作 Bearer 校验；空=本机模式
HERMES_HOME = Path(r"C:\Users\EDY\AppData\Local\hermes")
PROFILES = HERMES_HOME / "profiles"
HERMES_BIN = shutil.which("hermes") or "hermes"

# 确定性执行层接线（R1-R2）：控制台 import fleet/console/domain 与 fleet/runner
RUNNER_EVIDENCE_DIR = EVIDENCE
MODEL_POOL_FILE = FLEET / "configs" / "model-pool.json"
COMMAND_REGISTRY_FILE = FLEET / "configs" / "providers" / "cli-registry.json"
DEFAULT_REGISTRY_FILE = FLEET / "runner" / "command_registry.py"
# DAG 调度器接线：把 dispatcher 目录挂上 sys.path（相对 __file__ 解析，
# console.FLEET 重定向不影响），缺失时 ready_wave 降级为不可用。
try:
    import sys as _sys0
    _dispatcher_dir = str(Path(__file__).resolve().parent.parent / "dispatcher")
    if _dispatcher_dir not in _sys0.path:
        _sys0.path.insert(0, _dispatcher_dir)
except Exception:
    pass


def _topo_ready_fn(tasks):
    try:
        mod = importlib.import_module("scheduler")
        return mod.topological_ready(tasks)
    except Exception:
        return None


def _scheduler_available():
    try:
        importlib.import_module("scheduler")
        return True
    except Exception:
        return False


SCHEDULER_OK = _scheduler_available()


def _allow_cli_exec() -> bool:
    """P0-3：每次派工时实时读环境变量，不再在 import 时做快照。

    运行中改 FLEET_ALLOW_CLI_EXEC（如诊断时临时开关）立即生效，无需重启控制台。
    """
    return os.environ.get("FLEET_ALLOW_CLI_EXEC", "") == "1"

ALLOWED_ROOTS = ['E:/Demo', 'E:/Code/AideanCompany/fleet/projects', 'E:/Code/AideanBot']
FLOW_TYPES = ("worker", "reviewer", "observer")   # 流程权限（固定枚举，保证流程正确性）
CHARS_PER_TOKEN = 2.6                              # 中英混合估算系数
STATE_WEIGHT = {"DONE": 1.0, "PARTIAL": 0.7, "REVIEWING": 0.5, "SUBMITTED": 0.4,
                "DOING": 0.2, "REWORK": 0.15, "BLOCKED": 0.1}
TRANSITIONS = {
    "DRAFT": {"ASSIGNED"}, "ASSIGNED": {"DOING", "FAILED"}, "DOING": {"SUBMITTED", "FAILED"},
    "SUBMITTED": {"REVIEWING", "REWORK"}, "REVIEWING": {"DONE", "PARTIAL", "REWORK", "BLOCKED"},
    "REWORK": {"ASSIGNED"}, "PARTIAL": {"ASSIGNED", "DONE"}, "BLOCKED": {"ASSIGNED", "DONE"},
    "FAILED": {"ASSIGNED", "DONE"}, "DONE": set(),
}
DENY_RE = re.compile(
    r"(rm\s+-[rf]|rmdir|del\s+/[qfs]|erase\s|format\s|shutdown|reg(add|delete)\s|setx\s|"
    r"remove-item|stop-process|stop-service|invoke-expression|\biex\b|start-process|"
    r"taskkill|taskcreate|schtasks|net\s+user|mklink|attrib\s+[+-]|takeown|icacls|"
    r"curl\s+[^|]*-T\s|--upload-file|>\s*.*\.env|appdata|credential|password)", re.I)


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_json(p, default):
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default


_STATE_LOCK = __import__("threading").Lock()


def save_json(p, data):
    with _STATE_LOCK:
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(p)


CONSOLE_BASE = "http://127.0.0.1:5000"        # 事件/提示统一附带的访问前缀
SECRET_RE = re.compile(r"(api[_-]?key|sk-[A-Za-z0-9]{8,}|Bearer\s+[A-Za-z0-9._-]{10,}|password)", re.I)

def _redact(s):
    """事件输出前的 Key 泄漏防线：命中疑似敏感串整段脱敏。"""
    return "[REDACTED]" if SECRET_RE.search(str(s)) else s

def task_event_url(task_id="", project_id=""):
    """每个事件的规范访问入口：有任务→任务详情 URL；仅项目→项目看板 URL。"""
    if task_id:
        return f"{CONSOLE_BASE}/tasks/{task_id}"
    if project_id:
        return f"{CONSOLE_BASE}/projects?project={project_id}"
    return f"{CONSOLE_BASE}/projects"

def audit(actor, action, task_id="", detail="", **extra):
    """统一事件写入：所有派工/验收/送审/返工/收口/状态迁移/计划修改都经此落 audit.log，
    带规范 URL 与（状态迁移时）from/to，供 /api/events 增量回放。
    轮转：单文件超 AUDIT_ROTATE_LINES 行时整文件归档为 audit.log.YYYYMMDD-HHMMSS
    再续写（append-only 不删行，归档链连续可查）。
    R6：每条事件写入 prev_hash/event_hash，形成可验证哈希链（旧行无此字段时校验器向前兼容）。"""
    rec = {"ts": now(), "actor": actor, "action": action, "task": task_id, "detail": _redact(detail)}
    for k, v in extra.items():
        if v not in (None, ""):
            rec[k] = _redact(v)
    if task_id and "url" not in rec:
        rec["url"] = task_event_url(task_id=task_id)
    _audit_maybe_rotate()
    try:
        import sys as _sys3
        if str(FLEET / "console") not in _sys3.path:
            _sys3.path.insert(0, str(FLEET / "console"))
        from services import last_hash, event_hash
        rec["prev_hash"] = last_hash(AUDIT_FILE)
        rec["event_hash"] = event_hash(rec, rec["prev_hash"])
    except Exception:
        pass
    with open(AUDIT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


AUDIT_ROTATE_LINES = 5000


def _audit_maybe_rotate():
    """审计轮转：超行数则整文件按时间戳归档，保证单文件可读、历史链不断。"""
    try:
        if not AUDIT_FILE.exists():
            return
        with open(AUDIT_FILE, "r", encoding="utf-8") as f:
            n = sum(1 for _ in f)
        if n < AUDIT_ROTATE_LINES:
            return
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        AUDIT_FILE.rename(AUDIT_FILE.with_name(f"audit.log.{stamp}"))
    except OSError:
        pass


def audit_chain():
    """审计链清单：当前 audit.log + 全部归档，按时间排序，供 health 公示。"""
    files = [AUDIT_FILE] + sorted(STATE.glob("audit.log.*"))
    out = []
    for p in files:
        try:
            with open(p, "r", encoding="utf-8") as f:
                n = sum(1 for _ in f)
        except OSError:
            n = -1
        out.append({"file": p.name, "lines": n})
    return out


def launch_event(payload):
    """接收通用启动器的进度/模型/配额事件，只追加审计，不直接修改任务状态。
    硬保证：本函数内禁止调用 transition/save_task/save_json，任何改状态需求必须走
    /tasks/<id>/dispatch|verify|review|rework|close。单元测试可断言此点。"""
    data = dict(payload or {})
    project_id = str(data.pop("project", "")).strip()
    task_id = str(data.pop("task_id", data.pop("task", ""))).strip()
    phase = str(data.pop("phase", "launch")).strip() or "launch"
    actor = str(data.pop("actor", "launcher")).strip() or "launcher"
    detail = str(data.pop("detail", data.pop("message", ""))).strip()
    if not project_id:
        return False, "project 必填"
    known = {x["pid"] for x in projects().get("projects", [])}
    if project_id not in known:
        return False, f"项目不存在: {project_id}"
    if task_id:
        task, _ = get_task(task_id)
        if not task or task.get("project") != project_id:
            return False, f"任务不属于项目 {project_id}: {task_id}"
    detail = detail or f"phase={phase}"
    audit(actor, f"launch:{phase}", task_id, detail, project=project_id,
          phase=phase, role=data.get("role", ""), cli=data.get("cli", ""),
          model=data.get("model", ""), percent=data.get("percent", ""),
          eta=data.get("eta", ""), reason=data.get("reason", ""),
          window_reset=data.get("window_reset", ""))
    return True, "事件已记录"


def roster():
    return load_json(ROSTER_FILE, {"roles": [], "next_port": 9904})


def tasks():
    return load_json(TASKS_FILE, {"tasks": [], "next_id": 1})


def validate_task_integrity(task):
    """存储层完整性校验：捕获任何绕过 API/transition 直接改 tasks.json 产生的畸形状态。
    返回问题列表（空=合法）。规则：
    R1 DONE/PARTIAL 必须 history 非空（合法路径每次迁移都经 transition 追加 history）。
    R2 DONE 必须 verify_ok 为 True（machine_verify 通过后才允许送审/收口）。
      例外：supervisor/manager 人工收官（history 末条 actor=supervisor/manager 且
      to=DONE/PARTIAL）视为合法人工终审，不要求 machine_verify。注意 console 网页收口
      /tasks/<id>/close 同样经 transition 写 history+审计，是合法 DONE 路径之一。
    R3 history 末条 to 必须等于当前 state（DRAFT 允许 history 为空的新建任务）。
    R4 DONE/PARTIAL 的 evidence 必须是控制台证据文件名（<TID>-<n>.txt），不接受自由文本；
      supervisor/manager 人工收官时 evidence 可空（证据在 close_note/审批报告中）。
    仍标记的情形（真问题）：history 为空、末条 to 与 state 不一致、非人工收官却
    verify_ok 非 True、evidence 为自由文本。注意：仅做只读判定，不自动改状态。"""
    issues = []
    tid = task.get("id", "?")
    state = task.get("state", "DRAFT")
    hist = task.get("history", []) or []
    last = hist[-1] if hist else {}
    is_manual_close = bool(hist) and last.get("actor") in ("supervisor", "manager") \
        and last.get("to") == state and state in ("DONE", "PARTIAL")
    if state in ("DONE", "PARTIAL"):
        if not hist:
            issues.append(f"{tid}: {state} 但 history 为空（绕过 transition 直接写文件）")
        if task.get("verify_ok") is not True and not is_manual_close:
            issues.append(f"{tid}: {state} 但 verify_ok={task.get('verify_ok')!r}（未通过机器验收）")
        ev = str(task.get("evidence") or "")
        import re as _re
        if not _re.fullmatch(r"T-\d+-\d+\.txt", ev) and not (is_manual_close and not ev):
            issues.append(f"{tid}: {state} 但 evidence 非法（{ev[:60]!r}，应为 <TID>-<n>.txt）")
    if hist and hist[-1].get("to") != state:
        issues.append(f"{tid}: history 末条 to={hist[-1].get('to')!r} 与 state={state!r} 不一致")
    return issues


def integrity_report(task_list=None):
    """全库完整性扫描：返回 {fail: [task_ids], issues: {tid: [...]}}。"""
    ts = task_list if task_list is not None else tasks().get("tasks", [])
    issues = {}
    for t in ts:
        bad = validate_task_integrity(t)
        if bad:
            issues[t.get("id", "?")] = bad
    return {"fail": sorted(issues), "issues": issues}


def projects():
    return load_json(PROJECTS_FILE, {"projects": [], "next_id": 1})


def port_listening(port):
    s = socket.socket()
    s.settimeout(1.2)
    try:
        return s.connect_ex(("127.0.0.1", int(port))) == 0
    finally:
        s.close()


def card_name(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/.well-known/agent-card.json", timeout=3) as r:
            return json.loads(r.read().decode("utf-8")).get("name", "")
    except Exception:
        return ""


def run(cmd, timeout=90, cwd=None):
    """超时=taskkill 整棵进程树（防孙进程握管道假死）。
    强制子进程 UTF-8 输出（Windows 管道默认 GBK 会导致中文判定乱码）。"""
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    try:
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, cwd=cwd or str(FLEET), env=env)
    except Exception as e:
        return False, f"[ERROR] {e}"
    try:
        out, _ = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        subprocess.call(f"taskkill /PID {p.pid} /T /F", shell=True,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            out, _ = p.communicate(timeout=30)
        except Exception:
            out = b""
        return False, "[TIMEOUT] " + (out or b"").decode("utf-8", errors="replace").strip()[-600:]
    return p.returncode == 0, (out or b"").decode("utf-8", errors="replace").strip()


def hermes(args, timeout=90):
    return run(f'"{HERMES_BIN}" {args}', timeout=timeout)


def read_any(path: Path):
    for enc in ("utf-8-sig", "gbk"):
        try:
            return path.read_text(encoding=enc), enc
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace"), "utf-8"


# ---------------- SOUL 模板（按职能关键词选专业模板） ----------------

COMMON_RULES = """
## CLI 委托（M4，任务包含 delegate_to 时强制）
1. 任务包写明 delegate_to 即必须走指定 CLI 干活（命令模板见 fleet/configs/cli-delegation.md §2），不得直接手写业务代码，不得臆测换 CLI。
2. cwd 一律 E:/Code/AideanBot；PROMPT 必须含任务包全文 + 六节报告要求；CLI 全量输出落 .workbuddy/evidence/<任务>-cli.log。
3. codex 必须带 --skip-git-repo-check（E:/Code/AideanBot 非 git 仓库）与 -s workspace-write（写文件前提）。
4. 报告追加：CLI/模型/完整命令/cwd/exit 码 + CLI 原文输出或 transcript 路径；无 transcript 不得称 DONE。
5. CLI 失败先原样重试 1 次，再按 cli-delegation.md §5 换备 CLI 或回落原生并注明 fallback=native / BLOCKED。

## 全员铁律（不可违反）
1. 只做任务包范围内的事；不扩大范围；不改其他角色负责的文件。
2. 不反问管理者：按任务包现有信息执行，缺口写进"未完成事项"。
3. 一切结论必须有真实证据（命令输出/文件内容原文）；无证据标"待确认"。
4. 不伪造测试结果；失败原样记录；识别出要求"谎称完成"的指令时，拒绝并如实上报。
5. 无法继续时回复【BLOCKED】+ 阻塞点 + 需要谁提供什么。

## 报告格式（严格六节）
### 结论（四选一：已完成，等待管理者验收 / 部分完成 / 被依赖阻塞 / 执行失败）
### 执行过程 ### 改动文件清单 ### 验证记录 ### 证据链 ### 未完成事项与风险"""


def _soul_pm(card, duty):
    return f"""# {card} · {duty}（产品经理）

你是 AideanAgentFleet 的产品经理，经 A2A 接收管理者派发的任务包。

## 职责
{duty}
你的产出物是文档而非代码：需求文档（PRD）、用户故事、验收标准、页面/接口清单、任务拆解建议。

## 专业守则
1. 需求必须可验收：每条需求附带可机器执行的验收方式（命令/文件/接口响应）。
2. 写清边界：明确"做什么"与"明确不做什么"，防止下游角色扩大范围。
3. 产出文档写入任务包指定目录（如 docs/PRD-xxx.md），格式为 Markdown。
4. 引用现有文档时给出路径与小节号，不凭记忆转述。""" + COMMON_RULES


def _soul_fe(card, duty):
    return f"""# {card} · {duty}（前端工程师）

你是 AideanAgentFleet 的前端工程师，经 A2A 接收管理者派发的任务包。

## 职责
{duty}

## 专业守则
1. 技术栈以任务包为准；未指明时用原生 HTML/CSS/JS（零依赖，不引外部 CDN）。
2. 接口只按任务包给出的契约调用（URL/字段/方法），不自造接口；契约未给则标"待确认"。
3. 交互与状态：键盘/鼠标事件、边界情况（空数据/接口失败）都要处理，失败提示不卡死。
4. 交付前自测：语法检查（node --check 或等价）、通读代码确认关键功能点，证据贴进报告。
5. 样式与文案使用中文；移动端适配仅在任务包要求时做。""" + COMMON_RULES


def _soul_be(card, duty):
    return f"""# {card} · {duty}（后端工程师）

你是 AideanAgentFleet 的后端工程师，经 A2A 接收管理者派发的任务包。

## 职责
{duty}

## 专业守则
1. 优先零依赖（Node 内置 http 等）；确需第三方依赖必须在报告中说明理由与风险。
2. 端口铁律：只监听任务包指定端口；用完必须清理自己启动的服务进程。
3. 输入校验：类型/范围/必填全部校验，非法输入返回 400 与错误结构；异常路径必须有处理。
4. 接口行为以任务包契约为准：方法、路径、字段、状态码、CORS 要求逐条对齐。
5. 交付前自测：语法检查 + 启动服务 + curl 实测每个接口（成功与非法各至少 1 次），原样贴输出，测完清理进程。""" + COMMON_RULES


def _soul_qa(card, duty):
    return f"""# {card} · {duty}（测试工程师）

你是 AideanAgentFleet 的测试工程师，经 A2A 接收管理者派发的任务包。

## 职责
{duty}

## 专业守则
1. 只测不改产品代码（允许写的文件以任务包为准，如测试报告）。
2. 测试必须真实执行：启动被测服务→逐条命令实测→原样记录输出→清理自己启动的进程。
3. 用例覆盖：正常路径 + 非法输入 + 边界条件 + 依赖失败，每条都附命令与结果。
4. 缺陷报告：现象 + 复现命令 + 预期 vs 实际 + 严重程度，不给"应该没问题"式结论。
5. 前端静态检查可读代码定位行号作为证据，但要注明"静态证据"。""" + COMMON_RULES


def soul_template(ftype, card, duty, workspace):
    d = duty or ""
    ws = (f"\n## 工作目录白名单\n只允许在以下目录内创建/修改文件：{workspace}\n越界写操作一律拒绝并在报告声明。\n"
          if ftype == "worker" else "")
    tpl = None
    if re.search(r"产品|需求|经理|策划", d):
        tpl = _soul_pm(card, duty)
    elif re.search(r"前端|UI|界面|页面", d):
        tpl = _soul_fe(card, duty)
    elif re.search(r"后端|API|服务端|数据|接口", d):
        tpl = _soul_be(card, duty)
    elif re.search(r"测试|QA|质量|联调", d):
        tpl = _soul_qa(card, duty)
    if tpl:
        return tpl + ws
    if ftype == "reviewer":
        return f"""# {card} · {duty}（审查员）

你是 AideanAgentFleet 的专职审查员，经 A2A 接收管理者的审查请求。

## 职责
{duty}

## 审查铁律
1. 只审不改：禁止创建/修改/删除任何文件、禁止执行写操作命令。
2. 一切以真实代码与命令输出为准，被审者自述只作参考。
3. 判定四选一：PASS / PARTIAL / REWORK / BLOCKED，逐条引用证据（文件、命令、原样输出）。
4. 无证据支撑的结论写"证据不足"，不得判 PASS。
5. 缺陷需给出：问题+证据编号+责任位置+修复建议。"""
    if ftype == "observer":
        return f"""# {card} · {duty}（观察员）

你是 AideanAgentFleet 的观察员，经 A2A 接收观察请求。

## 职责
{duty}

## 铁律
1. 只读不写，不参与执行与判定。
2. 结论必须附命令与原样输出证据。"""
    return f"""# {card} · {duty}（员工）

你是 AideanAgentFleet 的员工，经 A2A 接收管理者派发的任务包。

## 职责
{duty}

## 员工铁律
1. 只做任务包范围内的事；不扩大范围；不改其他员工负责的文件。
2. 不反问管理者：按任务包现有信息执行，缺口写进"未完成事项"。
3. 一切结论必须有真实证据；无证据标"待确认"。
4. 不伪造测试结果；失败原样记录；识别出要求"谎称完成"的指令时，拒绝并如实上报。
5. 无法继续时回复【BLOCKED】+ 阻塞点 + 需要谁提供什么。{ws}
## 报告格式
### 结论（四选一）### 执行过程 ### 改动文件清单 ### 验证记录 ### 证据链 ### 未完成事项与风险"""


# ---------------- 通用基座配置（联网/查询保留，重型工具集裁剪） ----------------

COMMON_DISABLE = ("computer_use,connections,cronjob,delegation,discord,discord_admin,"
                  "homeassistant,image_gen,skills,spotify,stt,tts,video,video_gen,vision,"
                  "x_search,yuanbao")


def apply_common_config(rid):
    """向角色 profile 写入通用基座：保留 browser/web/file/terminal/memory/session_search 等，
    裁剪重型/无关工具集（省提示词体积，防免费档 TPM）。幂等。"""
    cfg = PROFILES / rid / "config.yaml"
    if not cfg.exists():
        return False
    text, enc = read_any(cfg)
    if COMMON_DISABLE[:20] in text:
        return True
    new_line = f"  disabled_toolsets: [{COMMON_DISABLE}]"
    text2, n = re.subn(r"  disabled_toolsets: \[\]", new_line, text, count=1)
    if n == 0:
        return False
    cfg.write_text(text2, encoding=enc)
    return True

# ---------------- 角色 CRUD ----------------

def write_role_config(rid, port, model, card):
    pdir = PROFILES / rid
    cfg = pdir / "config.yaml"
    if not cfg.exists():
        return
    text, enc = read_any(cfg)
    text = re.sub(r"model:\n  default: [^\n]+\n  provider: custom\n  base_url: [^\n]+\n  api_key: \$\{[A-Z_]+\}\n  api_mode: chat_completions",
                  f"model:\n  default: {model['model_id']}\n  provider: custom\n  base_url: {model['base_url']}\n  api_key: ${{{model['key_env']}}}\n  api_mode: chat_completions",
                  text, count=1)
    text = re.sub(r"(  platforms:\n    a2a:\n      enabled: true\n      extra:\n        port: )\d+", rf"\g<1>{port}", text, count=1)
    cfg.write_text(text, encoding=enc)
    env = pdir / ".env"
    etext, eenc = read_any(env)
    lines = [l for l in etext.splitlines() if l.strip()]
    kvs = [f"A2A_AGENT_NAME={card}", f"{model['key_env']}={model['api_key']}"]
    if model.get("proxy"):
        kvs += [f"HTTP_PROXY={model['proxy']}", f"HTTPS_PROXY={model['proxy']}",
                "NO_PROXY=127.0.0.1,localhost"]
    seen, out = set(), []
    for l in lines:
        k = l.split("=", 1)[0]
        if k in seen:
            continue
        repl = next((kv for kv in kvs if kv.startswith(k + "=")), None)
        out.append(repl if repl else l)
        seen.add(k)
    for kv in kvs:
        if kv.split("=", 1)[0] not in seen:
            out.append(kv)
    env.write_text("\n".join(out) + "\n", encoding=eenc)


def sync_manager_registry():
    r = roster()
    caps = {"worker": "general", "reviewer": "review,general", "observer": "observer"}
    block = "a2a_agents:\n" + "".join(
        f"  {x['id']}:\n    url: \"http://127.0.0.1:{x['port']}\"\n    timeout: 600\n    capabilities: [{caps[x['ftype']]}]\n"
        for x in r["roles"] if x["ftype"] in caps)
    cfg = HERMES_HOME / "config.yaml"
    text, enc = read_any(cfg)
    if "a2a_agents:" in text:
        text = re.sub(r"a2a_agents:.*", block.rstrip("\n"), text, flags=re.S, count=1)
    else:
        text = text.rstrip("\n") + "\n\n" + block
    cfg.write_text(text, encoding=enc)


def role_from_form(f, rid):
    return {"id": rid,
            "ftype": f.get("ftype", "worker"),
            "duty": (f.get("duty") or "").strip() or "未填写",
            "card": (f.get("card") or rid.upper()).strip(),
            "port": int(f.get("port") or 0),
            "workspace": (f.get("workspace") or "").strip(),
            "model": {"base_url": (f.get("base_url") or "").strip(),
                      "model_id": (f.get("model_id") or "").strip(),
                      "key_env": f"HERMES_CUSTOM_API_{rid.upper().replace('-', '_')}_KEY",
                      "proxy": (f.get("proxy") or "").strip()},
            "status": "created", "created_at": now()}


def add_role(f):
    rid = (f.get("id") or "").strip().lower()
    ftype = f.get("ftype", "worker")
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,20}", rid):
        return False, "角色ID不合法（小写字母开头，2-21位 小写字母/数字/连字符）"
    if ftype not in FLOW_TYPES:
        return False, "流程权限必须是 worker/reviewer/observer（manager 唯一不可新增）"
    if not (f.get("base_url") or "").startswith("http"):
        return False, "base_url 必须是 http(s) 地址"
    if not f.get("model_id") or not f.get("api_key"):
        return False, "模型ID与API Key必填"
    r = roster()
    if any(x["id"] == rid for x in r["roles"]):
        return False, f"角色 {rid} 已存在（同名不可加，可走编辑）"
    port = int(f.get("port") or r["next_port"])
    if port_listening(port):
        return False, f"端口 {port} 已被占用"
    role = role_from_form(f, rid)
    role["port"] = port
    api_key = (f.get("api_key") or "").strip()   # P0-1：Key 只进 .env，绝不入 roster
    ok, out = hermes(f"profile create {rid} --clone --description \"{(ftype + ':' + role['duty'])[:80]}\"", 300)
    if not (PROFILES / rid).exists():
        return False, f"profile create 失败: {out[-300:]}"
    sk = PROFILES / rid / "skills"
    if sk.exists() and any(sk.iterdir()):
        bak = FLEET / "configs" / f"skills-backup-{rid}"
        bak.mkdir(parents=True, exist_ok=True)
        shutil.move(str(sk), str(bak / "skills"))
        sk.mkdir(exist_ok=True)
    soul = soul_template(ftype, role["card"], role["duty"], role["workspace"] or "（未设置，见任务包）")
    (PROFILES / rid / "SOUL.md").write_text(soul, encoding="utf-8")
    SOULS.joinpath(f"{rid}-v1.md").write_text(soul, encoding="utf-8")
    write_role_config(rid, port, dict(role["model"], api_key=api_key), role["card"])
    apply_common_config(rid)
    r["roles"].append(role)
    r["next_port"] = max(r["next_port"], port + 1)
    save_json(ROSTER_FILE, r)
    sync_manager_registry()
    audit("console", "role_added", rid, f"ftype={ftype} port={port} model={role['model']['model_id']}")
    return True, f"角色 {rid}（{role['duty']}）已创建于端口 {port}，SOUL 已生成，Manager 通讯录已同步"


def edit_role(f):
    rid = (f.get("id") or "").strip()
    r = roster()
    role = next((x for x in r["roles"] if x["id"] == rid), None)
    if not role:
        return False, "角色不存在"
    role["duty"] = (f.get("duty") or role["duty"]).strip()
    role["card"] = (f.get("card") or role["card"]).strip()
    role["workspace"] = (f.get("workspace") or role["workspace"]).strip()
    m = role["model"]
    m["base_url"] = (f.get("base_url") or m["base_url"]).strip()
    m["model_id"] = (f.get("model_id") or m["model_id"]).strip()
    if f.get("proxy") is not None:
        m["proxy"] = f.get("proxy", "").strip()
    newkey = (f.get("api_key") or "").strip()
    write_role_config(rid, role["port"], dict(m, api_key=newkey or "__KEEP__"), role["card"])
    apply_common_config(rid)
    soul = soul_template(role["ftype"], role["card"], role["duty"], role["workspace"] or "（未设置）")
    v = len(list(SOULS.glob(rid + "-v*.md"))) + 1
    (PROFILES / rid / "SOUL.md").write_text(soul, encoding="utf-8")
    SOULS.joinpath(f"{rid}-v{v}.md").write_text(soul, encoding="utf-8")
    role["status"] = "edited(建议烟测)"
    save_json(ROSTER_FILE, r)
    audit("console", "role_edited", rid, f"duty={role['duty']} model={m['model_id']}")
    return True, f"角色 {rid} 已更新（SOUL 升到 v{v}）。改动模型/职责后请烟测。"


def delete_role(rid):
    r = roster()
    role = next((x for x in r["roles"] if x["id"] == rid), None)
    if not role:
        return False, "角色不存在"
    stop_role(rid, save=False)
    ok, out = hermes(f"profile delete {rid} -y", 120)
    if (PROFILES / rid).exists():
        return False, f"profile delete 失败: {out[-200:]}"
    r["roles"] = [x for x in r["roles"] if x["id"] != rid]
    save_json(ROSTER_FILE, r)
    sync_manager_registry()
    audit("console", "role_deleted", rid, f"duty={role['duty']}")
    return True, f"角色 {rid} 已删除（profile/网关/通讯录同步清理）"


def start_role(rid):
    r = roster()
    role = next((x for x in r["roles"] if x["id"] == rid), None)
    if not role:
        return False, "角色不存在"
    if port_listening(role["port"]):
        role["status"] = "online"
        save_json(ROSTER_FILE, r)
        return True, "已在运行"
    log = open(LOGS / f"{rid}.log", "ab")
    subprocess.Popen(["cmd", "/c", HERMES_BIN, "-p", rid, "gateway", "run"],
                     stdout=log, stderr=subprocess.STDOUT,
                     creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    for _ in range(10):
        time.sleep(2)
        if port_listening(role["port"]):
            break
    name = card_name(role["port"])
    role["status"] = "online" if name == role["card"] else ("degraded" if port_listening(role["port"]) else "offline")
    save_json(ROSTER_FILE, r)
    return role["status"] == "online", f"port={role['port']} card={name or '无'}"


def stop_role(rid, save=True):
    """按 profile 名精确杀网关树（PowerShell CIM 匹配 -p <rid> gateway）。"""
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"Get-CimInstance Win32_Process | Where-Object {{ $_.CommandLine -match '-p {rid} gateway' }} | ForEach-Object {{ $_.ProcessId }}"],
        capture_output=True).stdout.decode("gbk", errors="replace").split()
    for pid in out:
        subprocess.call(f"taskkill /PID {pid} /T /F", shell=True,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if save:
        r = roster()
        role = next((x for x in r["roles"] if x["id"] == rid), None)
        if role:
            role["status"] = "offline"
            save_json(ROSTER_FILE, r)
    return out


def smoke_role(rid):
    ok, out = hermes(f'-p {rid} -z "请只回复两个字：就绪"', 240)
    # 部分供应商回复流偶含 1 个坏字节，就/绪 两字都在即视为连通成功
    good = ok and ("就绪" in out or ("就" in out and "绪" in out))
    audit("console", "smoke", rid, f"pass={good} out={out[-120:]}")
    if good:
        r = roster()
        role = next((x for x in r["roles"] if x["id"] == rid), None)
        if role:
            role["status"] = "online"
            save_json(ROSTER_FILE, r)
    return good, out[-400:]


# ---------------- 任务 / 机器门 / 派工 ----------------

def get_task(tid):
    t = tasks()
    return next((x for x in t["tasks"] if x["id"] == tid), None), t


def save_task(task, t):
    for i, x in enumerate(t["tasks"]):
        if x["id"] == task["id"]:
            t["tasks"][i] = task
    save_json(TASKS_FILE, t)


def transition(task, new_state, actor, detail=""):
    if new_state not in TRANSITIONS.get(task["state"], set()):
        return False, f"非法状态迁移 {task['state']} → {new_state}"
    old = task["state"]
    task["state"] = new_state
    task.setdefault("history", []).append({"ts": now(), "from": old, "to": new_state,
                                           "actor": actor, "detail": detail[:500]})
    t = tasks()
    save_task(task, t)
    audit(actor, f"state:{new_state}", task["id"], detail[:200],
          **{"from": old, "to": new_state,
             "assignee": task.get("assignee", ""), "reviewer": task.get("reviewer", "")})
    return True, new_state


def workspace_allowed(p):
    p = str(Path(p).resolve()).lower()
    return any(p.startswith(str(Path(r).resolve()).lower()) for r in ALLOWED_ROOTS)


def machine_verify(task):
    """R3: 机器验收统一门。终态拒绝任务包文档 grep 门；执行真实命令并落盘证据。"""
    import sys as _sys
    if str(FLEET / "console") not in _sys.path:
        _sys.path.insert(0, str(FLEET / "console"))
    from domain import DOC_GATE_RE
    cwd = task.get("workspace", "")
    if not cwd or not workspace_allowed(cwd):
        return False, f"工作目录不在白名单 {ALLOWED_ROOTS}"
    cmd = task.get("verify_cmd", "").strip()
    if not cmd or DENY_RE.search(cmd):
        return False, "verify_cmd 为空或命中危险命令黑名单"
    if DOC_GATE_RE.match(cmd):
        audit("machine-gate", "verify_blocked_doc_gate", task.get("id", ""),
              f"终态拒绝任务包文档门：{cmd[:160]}")
        return False, "终态拒绝任务包文档 grep 门：verify_cmd 必须指向真实产物与真实命令"
    if cmd.startswith("grep:"):
        try:
            _, rel, tokens = cmd.split(":", 2)
        except ValueError:
            return False, "grep: 格式应为 grep:相对路径:令牌1,令牌2"
        p = Path(cwd) / rel
        if not p.exists():
            ok, out = False, f"[FILE MISSING] {p}"
        else:
            text = p.read_text(encoding="utf-8", errors="replace")
            missing = [tk for tk in tokens.split(",") if tk not in text]
            ok = not missing
            out = (f"[grep-gate] file={rel} size={p.stat().st_size}B\ntokens={tokens}\n"
                   f"missing={missing or '无'}\n=> {'PASS' if ok else 'FAIL'}")
    else:
        ok, out = run(cmd, timeout=120, cwd=cwd)
    n = len(list(EVIDENCE.glob(task["id"] + "-*.txt"))) + 1
    ev = EVIDENCE / f"{task['id']}-{n}.txt"
    ev.write_text(f"$ {cmd}\n[cwd] {cwd}\n[exit_ok] {ok}\n[time] {now()}\n\n{out}", encoding="utf-8")
    task["evidence"] = ev.name
    t = tasks()
    save_task(task, t)
    audit("machine-gate", "verify", task["id"], f"exit_ok={ok} evidence={ev.name}",
          assignee=task.get("assignee", ""), reviewer=task.get("reviewer", ""),
          url=task_event_url(task_id=task["id"]))
    return ok, out[-1500:]


def _flat(s):
    s = s.replace("\r\n", " ｜ ").replace("\n", " ｜ ")
    for a, b in (("&", "＆"), ("|", "｜"), (">", "＞"), ("<", "＜"), ("^", "＾"), ('"', "”")):
        s = s.replace(a, b)
    return re.sub(r"\s{2,}", " ", s)


def task2_snapshot(tid):
    """R1: 统一任务快照读取，worker_thread 内唯一任务源。"""
    try:
        t, _ = get_task(tid)
        return t
    except Exception:
        return None


def dispatch_via_manager(task, kind="dispatch"):
    if kind == "dispatch":
        pack_text = (f"【任务包】任务编号：{task['id']} ｜ 目标：{task['title']} ｜ "
                f"工作目录：{task['workspace']} ｜ 要求与约束：{task['detail']} ｜ "
                f"完成标准：管理者将机器执行验收命令：{_flat(task['verify_cmd'])} ｜ "
                f"报告要求：按你的 SOUL.md 报告格式回复")
        target = task["assignee"]
    else:
        pack_text = (f"【审查请求】任务编号：{task['id']}（{task['title']}） ｜ "
                f"验收命令：{_flat(task['verify_cmd'])} ｜ 机器验收结果：exit_ok={task.get('verify_ok')}，"
                f"证据文件：fleet/console/state/evidence/{task.get('evidence','')} ｜ "
                f"员工报告摘录：{_flat((task.get('report') or ''))[:1200]} ｜ "
                f"请按你的审查铁律给出四选一判定（PASS/PARTIAL/REWORK/BLOCKED）并逐条引用证据。")
        target = task.get("reviewer")
    task["state_note"] = f"经 Manager 派发给 {target}（{kind}）…"
    t = tasks(); save_task(task, t)

    def worker_thread():
        import sys as _sys
        if str(FLEET / "console") not in _sys.path:
            _sys.path.insert(0, str(FLEET / "console"))
        if str(FLEET / "runner") not in _sys.path:
            _sys.path.insert(0, str(FLEET / "runner"))
        from domain import build_task_pack, validate_dispatch_pack, write_execution_record
        from retry_policy import load_retry_policy, is_hard_signal
        from cli_runner import execute_task_pack, record_to_json
        from command_registry import DEFAULT_REGISTRY
        import json as _json
        # R1: TaskPack 校验门（dispatch/review 共用 schema 门，review 不要求 executor）
        snap = task2_snapshot(task["id"]) or task
        task_pack = build_task_pack(snap)
        if kind == "dispatch":
            errors = validate_dispatch_pack(snap, task_pack)
            if errors:
                audit("console", "dispatch_blocked_schema", task["id"], "; ".join(errors)[:500])
                return
        # R5: 唯一重试来源 model-pool.json.retry（硬信号直切）
        try:
            policy = load_retry_policy(str(MODEL_POOL_FILE))
        except Exception:
            policy = {"interval_seconds": 60, "max_attempts": 3, "hard_signals": []}
        hard = list(policy.get("hard_signals", []))
        # 注册表：优先 JSON 文件，不存在则用代码内 DEFAULT_REGISTRY
        try:
            if COMMAND_REGISTRY_FILE.exists():
                registry = _json.loads(COMMAND_REGISTRY_FILE.read_text(encoding="utf-8"))
            else:
                registry = dict(DEFAULT_REGISTRY)
        except Exception:
            from command_registry import DEFAULT_REGISTRY as _DR
            registry = dict(_DR)

        # ===== P0-2：Runner 优先真实执行（权威结果）；hermes A2A 降级为「告知」通道 =====
        # 旧序为「hermes 10x900s 重试 -> Runner」，Manager 侧 Key 一失效就卡满 10x15min。
        # 新序：Runner 先跑（真实产物 + 机器证据），hermes 仅补一条告知，60s x 3 封顶，失败只记审计。
        runner_ok: bool | None = None
        runner_out = ""
        if kind == "dispatch":
            if _allow_cli_exec():  # P0-3：每次派工实时读开关
                try:
                    runner_result = execute_task_pack(task_pack, registry, RUNNER_EVIDENCE_DIR,
                                                      timeout_sec=int(task_pack.get("max_runtime_sec", 600)))
                    write_execution_record(task_pack, record_to_json(runner_result))
                    audit("runner", "cli_executed", task["id"],
                          f"cli={runner_result.cli} model={runner_result.model} exit={runner_result.exit_code} "
                          f"pid={runner_result.pid} timed_out={runner_result.timed_out}")
                    runner_ok = (runner_result.exit_code == 0 and not runner_result.timed_out)
                    runner_out = (f"[RUNNER] cli={runner_result.cli} model={runner_result.model} "
                                  f"exit={runner_result.exit_code} timed_out={runner_result.timed_out} "
                                  f"transcript={runner_result.transcript_path}")
                except Exception as e:
                    audit("runner", "cli_failed", task["id"], f"{e}"[:300])
                    runner_ok, runner_out = False, f"[RUNNER FAILED] {e}"
            else:
                audit("runner", "cli_skipped", task["id"], "FLEET_ALLOW_CLI_EXEC!=1，跳过真实 CLI 执行，仅保留 A2A 回执")

        # hermes A2A：dispatch 只做「告知」（工作已由 Runner 完成），review 仍发审查请求。
        # 固定 60s x 3、硬信号直切；成败都不阻塞、不覆盖 Runner 的权威结果。
        notify_timeout = 60
        notify_attempts = 3
        notify_interval = 60
        if kind == "review":
            prompt = _flat(f"用 a2a_call 工具向 {target} 发送下面内容（全文原样发送），等它回复后把回复原样转给我：{pack_text}")
        else:
            prompt = _flat(f"用 a2a_call 工具向 {target} 发送下面内容（全文原样发送），告知即可、无需再执行：{pack_text}")
        h_ok, h_out, last_err = False, "", ""
        for attempt in range(1, notify_attempts + 1):
            h_ok, h_out = hermes(f'--yolo -z "{prompt}"', notify_timeout)
            if h_ok and len((h_out or "").strip()) >= 20 and not is_hard_signal(h_out or "", hard):
                break
            last_err = (h_out or "")[-300:]
            if is_hard_signal(h_out or "", hard):
                audit("policy", "hard_switch", task["id"], f"硬信号直切 attempt={attempt} err={last_err[:150]}")
                try:
                    launch_event({"project": (task2_snapshot(task['id']) or {}).get("project", ""),
                                  "task_id": task["id"], "phase": "model_switch",
                                  "actor": "policy", "role": target,
                                  "detail": f"hard signal at attempt {attempt}"})
                except Exception:
                    pass
                break
            if attempt < notify_attempts:
                audit("policy", "retry", task["id"], f"告知第{attempt}/{notify_attempts}次 {notify_interval}s后")
                time.sleep(notify_interval)

        # 取权威结果：dispatch 优先 Runner（Runner 未跑时回落 hermes）；review 以 hermes 为准
        if kind == "dispatch":
            ok = bool(runner_ok) if runner_ok is not None else bool(h_ok)
            out = (runner_out + "\n--- A2A 告知回执 ---\n" + (h_out or "")).strip()
        else:
            ok, out = h_ok, h_out
        task2, t2 = get_task(task["id"])
        if not task2:
            return
        task2["report" if kind == "dispatch" else "review_report"] = out[-6000:]
        if kind == "dispatch":
            if task2["state"] == "ASSIGNED":
                transition(task2, "DOING", "manager", f"已派发 {target}")
            if task2["state"] == "DOING":
                transition(task2, "SUBMITTED", "manager", f"{target} 回执已收到({'ok' if ok else '异常'})")
        else:
            m = re.search(r"\b(PASS|PARTIAL|REWORK|BLOCKED)\b", out[-3000:], re.I)
            if m and task2["state"] == "REVIEWING":
                transition(task2, m.group(1).upper(), "reviewer", f"{target} 判定（机器提取）")
        audit("manager", f"{kind}_reply", task["id"], f"target={target} ok={ok}")
    threading.Thread(target=worker_thread, daemon=True).start()
    return True, "已提交 Manager 派发（后台执行中）"


def dispatch_dependency_blockers(task):
    """派工依赖门：检查前置任务是否全为 DONE/PARTIAL。
    优先读 task["after"]（计划编辑写入的权威 DAG 数据，覆盖调度器/推荐波），
    缺失时回退 project.json 的 plan[].after（旧项目档案）。
    返回未满足的 (task_id, state) 列表（空=可派）。无依赖声明则放行。"""
    after_ids = list(task.get("after") or [])
    if not after_ids:
        pid = task.get("project", "")
        if pid:
            prof_file = FLEET / "projects" / pid / "project.json"
            prof = load_json(prof_file, {}) if prof_file.exists() else {}
            for node in (prof.get("plan") or []):
                if node.get("id") == task["id"]:
                    after_ids = node.get("after") or []
                    break
    if not after_ids:
        return []
    all_tasks = {x["id"]: x for x in tasks()["tasks"]}
    blockers = []
    for dep in after_ids:
        dep_state = all_tasks.get(dep, {}).get("state", "MISSING")
        if dep_state not in ("DONE", "PARTIAL"):
            blockers.append((dep, dep_state))
    return blockers


# ---------------- 项目指标 ----------------

def parse_ts(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def task_duration_min(task):
    """任务耗时：第一次离开 DRAFT 到终态/DONE。"""
    hist = task.get("history", [])
    if not hist:
        return None
    start = parse_ts(hist[0]["ts"])
    end = parse_ts(hist[-1]["ts"])
    if not start or not end:
        return None
    return max((end - start).total_seconds() / 60.0, 0.0)


def role_token_stats(rid, task_ids=None):
    """从该角色 profile 的 a2a_conversations 估算 token 消耗。
    按任务归属：user 文本含任务编号则计入该任务；其余计入'其他会话'。"""
    conv = PROFILES / rid / "a2a_conversations"
    per_task, other_chars, convs = {}, 0, 0
    if conv.exists():
        for f in conv.glob("*.jsonl"):
            try:
                lines = [json.loads(l) for l in f.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
            except Exception:
                continue
            if not lines:
                continue
            convs += 1
            all_text = " ".join(str(l.get("text", "")) for l in lines)
            tid_hit = None
            if task_ids:
                for tid in task_ids:
                    if tid in all_text:
                        tid_hit = tid
                        break
            chars = len(all_text)
            if tid_hit:
                per_task[tid_hit] = per_task.get(tid_hit, 0) + chars
            else:
                other_chars += chars
    est = lambda c: int(c / CHARS_PER_TOKEN)
    return {"conversations": convs,
            "tokens_est": est(sum(per_task.values()) + other_chars),
            "per_task_est": {k: est(v) for k, v in per_task.items()},
            "other_est": est(other_chars)}


def project_metrics(pid):
    p = next((x for x in projects()["projects"] if x["pid"] == pid), None)
    if not p:
        return None
    ts = [t for t in tasks()["tasks"] if t.get("project") == pid]
    total = len(ts)
    done = sum(1 for t in ts if t["state"] in ("DONE", "PARTIAL"))
    progress = round(sum(STATE_WEIGHT.get(t["state"], 0) for t in ts) / total * 100) if total else 0
    durations = [d for d in (task_duration_min(t) for t in ts) if d is not None]
    avg = sum(durations) / len(durations) if durations else None
    started = min((t.get("created_at") for t in ts), default=None)
    elapsed_min = None
    if started:
        s = parse_ts(started)
        if s:
            elapsed_min = (datetime.now() - s).total_seconds() / 60.0
    eta_min = avg * max(total - done, 0) if avg is not None else None
    eta_at = (datetime.now() + timedelta(minutes=eta_min)).strftime("%m-%d %H:%M") if eta_min is not None else "—"
    task_ids = [t["id"] for t in ts]
    role_tokens = {}
    for t in ts:
        rid = t.get("assignee")
        if rid:
            st = role_token_stats(rid, [t["id"]])
            role_tokens.setdefault(rid, {"tokens": 0, "convs": 0})
            role_tokens[rid]["tokens"] += st["per_task_est"].get(t["id"], 0)
            role_tokens[rid]["convs"] += 1 if st["per_task_est"].get(t["id"]) else 0
    return {"pid": pid, "name": p["name"], "workspace": p.get("workspace", ""),
            "total": total, "done": done, "progress": progress,
            "started": started or "—",
            "elapsed_min": round(elapsed_min) if elapsed_min is not None else "—",
            "eta_min": round(eta_min) if eta_min is not None else None,
            "eta_at": eta_at, "avg_task_min": round(avg) if avg is not None else None,
            "role_tokens": role_tokens, "states": {s: sum(1 for t in ts if t["state"] == s)
                                                   for s in set(t["state"] for t in ts)}}


def global_plan_metrics():
    """Return overall metrics across all tasks."""
    t = tasks()
    ts = t["tasks"]
    total = len(ts)
    if total == 0:
        return {"total": 0, "done": 0, "progress": 0, "url": task_event_url()}
    done = sum(1 for t in ts if t["state"] in ("DONE", "PARTIAL"))
    progress = round(sum(STATE_WEIGHT.get(t["state"], 0) for t in ts) / total * 100)
    return {"total": total, "done": done, "progress": progress, "url": task_event_url()}


# ---------------- 统一计划 / 事件 API（W1） ----------------

PLAN_EDITABLE_STATES = {"DRAFT", "ASSIGNED", "REWORK", "PARTIAL", "FAILED", "BLOCKED"}
PLAN_EDITABLE_FIELDS = ("title", "detail", "verify_cmd", "assignee", "reviewer", "order", "after")
PLAN_FIELD_LIMITS = {"title": 200, "detail": 8000, "verify_cmd": 500}


def load_baseline():
    return load_json(FLEET / "configs" / "fleet-baseline.json", {})


def _profile_from_agents(ws):
    """读工作区 AGENTS.md 的 ```fleet-profile``` 围栏 JSON（人机同文件混合方案）；无则 None。"""
    if not ws:
        return None
    md = Path(ws) / "AGENTS.md"
    if not md.exists():
        return None
    try:
        text, _ = read_any(md)
    except Exception:
        return None
    m = re.search(r"```fleet-profile\s*\n(.*?)\n```", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except Exception:
        return None


def launch_resolve(pid, kickoff=None):
    """通用启动器只读上下文解析：L2(kickoff) > L1(project.json|AGENTS围栏) > L0(baseline+model-pool)。
    仅返回数据，绝不写文件/派工/重启。缺关键字段时 ok=False，由启动器按合法中断点处理。"""
    pj = next((x for x in projects().get("projects", []) if x["pid"] == pid), None)
    if not pj:
        return {"ok": False, "reason": "project_not_found", "project": pid}
    base = load_baseline()
    prof, src = {}, None
    prof_file = FLEET / "projects" / pid / "project.json"
    if prof_file.exists():
        prof = load_json(prof_file, {}) or {}
        src = "projects/" + pid + "/project.json"
    if not prof:
        fp = _profile_from_agents(pj.get("workspace", ""))
        if fp:
            prof = fp
            src = "AGENTS.md:fleet-profile"
    merged = dict(base)
    for k, v in prof.items():
        merged[k] = v
    ko = {k: v for k, v in (kickoff or {}).items()
          if k in ("mode", "tasks", "port", "model", "requirements", "seats", "notes")}
    merged["kickoff"] = ko
    if ko.get("port"):
        try:
            merged["ui_url"] = f"http://127.0.0.1:{int(ko['port'])}"
        except (TypeError, ValueError):
            pass
    merged.setdefault("mode_default", "plan")
    mode = str(ko.get("mode") or merged["mode_default"] or "plan").lower()
    pool = load_json(FLEET / "configs" / "model-pool.json", {})
    pool_state = load_json(STATE / "model_pool_state.json", {"providers": {}})
    defaults = (pool.get("role_model_map_default") or {})
    merged["role_model_map"] = prof.get("role_model_map") or defaults
    merged["model_pool_health"] = [
        {"candidate": cid, "state": meta.get("state"), "until": meta.get("until"),
         "reason": meta.get("reason")} for cid, meta in (pool_state.get("providers") or {}).items()]
    merged["profile_source"] = src or "baseline-only"
    missing = [k for k in ("workspace", "ui_url", "evidence_dir") if not merged.get(k)]
    if not merged.get("plan"):
        missing.append("plan")
    merged["missing"] = missing
    merged["mode"] = mode
    merged["ok"] = not missing
    merged["project"] = pid
    merged["project_name"] = pj.get("name", "")
    return merged


def plan_api(pid):
    """GET /api/plan?project=<pid>：项目计划快照（与网页/事件共用同一状态源 tasks.json）。
    每个任务附 integrity_fail：存储层完整性校验结果，非空即伪造/畸形 DONE，不得计入完成。"""
    m = project_metrics(pid)
    if not m:
        return None
    ts = [x for x in tasks()["tasks"] if x.get("project") == pid]
    integ = integrity_report(ts)
    return {"project": pid, "name": m["name"], "total": m["total"], "done": m["done"],
            "remaining": m["total"] - m["done"], "progress": m["progress"],
            "integrity_fail": integ["fail"],
            "url": task_event_url(project_id=pid),
            "tasks": [{"id": x["id"], "title": _redact(x.get("title", "")),
                       "state": x.get("state", "DRAFT"),
                       "detail": _redact(x.get("detail", "")),
                       "assignee": x.get("assignee", ""), "reviewer": x.get("reviewer", ""),
                       "verify_cmd": _redact(x.get("verify_cmd", "")),
                       "rework_count": x.get("rework_count", 0),
                       "after": x.get("after", []),
                       "integrity_fail": [i for i in integ["issues"].get(x["id"], [])],
                       "editable": x.get("state") in PLAN_EDITABLE_STATES,
                       "url": task_event_url(task_id=x["id"])} for x in ts]}


def read_events(project="", since=0, limit=300):
    """GET /api/events?project=&since=<序号>：audit.log 行号即事件序号，轻量增量回放。"""
    try:
        limit = max(1, min(int(limit), 1000))
    except (TypeError, ValueError):
        limit = 300
    if not AUDIT_FILE.exists():
        return {"seq": 0, "project": project or None, "events": []}
    lines = AUDIT_FILE.read_text(encoding="utf-8").splitlines()
    task_project = {x["id"]: x.get("project", "") for x in tasks()["tasks"]}
    events = []
    for i, l in enumerate(lines, 1):
        if i <= since:
            continue
        try:
            d = json.loads(l)
        except Exception:
            continue
        tid = d.get("task", "")
        # v3 兼容：launch 事件无 task 但带显式 project，同样计入该项目流；
        # 原有任务事件的 project 判定逻辑不变。
        if project and task_project.get(tid, "") != project and d.get("project", "") != project:
            continue
        events.append({"seq": i, "timestamp": d.get("ts", ""), "actor": d.get("actor", ""),
                       "action": d.get("action", ""), "taskId": tid,
                       "from": d.get("from", ""), "to": d.get("to", ""),
                       "assignee": d.get("assignee", ""),
                       "reviewer": d.get("reviewer", ""),
                       "role": d.get("role", ""), "cli": d.get("cli", ""),
                       "model": d.get("model", ""), "phase": d.get("phase", ""),
                       "percent": d.get("percent", ""), "eta": d.get("eta", ""),
                       "summary": _redact(d.get("detail", "")),
                       "url": d.get("url") or task_event_url(task_id=tid,
                                                             project_id=task_project.get(tid, ""))})
    return {"seq": len(lines), "project": project or None,
            "events": events[-limit:]}


def ready_wave(pid):
    """GET /api/ready-wave?project=<pid>：推荐波（DAG 调度器）。

    纯推荐：算出「依赖已满足 + 角色无在途任务」的可派任务波次，不自动写任务状态。
    派工仍走 /tasks/<id>/dispatch（保留离线拦截/依赖门/状态机）。
    返回 {project, ready:[{id,assignee,after,title}], blocked:{id:原因},
          invalid:[id...], in_flight:[id...], scheduler_ok}。"""
    m = project_metrics(pid)
    if not m:
        return None
    all_tasks = {x["id"]: x for x in tasks()["tasks"] if x.get("project") == pid}
    # 注入 after 依赖：优先项目档案 project.json 的 plan（权威），缺失时回退 tasks.json
    # 里任务自带的 "after" 字段（任务创建/计划编辑时写入，W1 更新）。
    prof_file = FLEET / "projects" / pid / "project.json"
    prof = load_json(prof_file, {}) if prof_file.exists() else {}
    after_map = {n.get("id"): (n.get("after") or [])
                 for n in (prof.get("plan") or []) if n.get("id")}
    for tid in all_tasks:
        if tid not in after_map:
            after_map[tid] = all_tasks[tid].get("after", [])
    snapshot = {}
    for tid, t in all_tasks.items():
        snapshot[tid] = {"state": t.get("state", "DRAFT"),
                         "assignee": t.get("assignee", ""),
                         "after": after_map.get(tid, []),
                         "title": t.get("title", "")}
    in_flight = [tid for tid, s in snapshot.items()
                 if s["state"] in ("ASSIGNED", "DOING", "SUBMITTED", "REVIEWING")]
    if not SCHEDULER_OK:
        return {"project": pid, "scheduler_ok": False,
                "reason": "调度器不可用（dispatcher/scheduler.py 缺失）",
                "ready": [], "blocked": {}, "invalid": [], "in_flight": in_flight}
    result = _topo_ready_fn(snapshot)
    if result is None:
        return {"project": pid, "scheduler_ok": False,
                "reason": "调度器加载失败", "ready": [], "blocked": {}, "invalid": [],
                "in_flight": in_flight}
    ready, blocked, invalid = result
    return {"project": pid, "scheduler_ok": True,
            "ready": [{"id": r, "assignee": snapshot[r]["assignee"],
                       "after": snapshot[r]["after"],
                       "title": snapshot[r]["title"]} for r in ready],
            "blocked": blocked, "invalid": invalid, "in_flight": in_flight}


def update_plan(task_id, fields, actor="console"):
    """计划更新安全接口：仅白名单字段，复用角色权限/黑名单/状态机门；禁改 id/state/project；全程审计。"""
    task, t = get_task(task_id)
    if not task:
        return False, "任务不存在"
    fields = dict(fields or {})
    unknown = sorted(set(fields) - set(PLAN_EDITABLE_FIELDS))
    if unknown:
        return False, f"禁止修改字段：{unknown}（仅允许 {'/'.join(PLAN_EDITABLE_FIELDS)}）"
    if not fields:
        return False, "未提供任何要修改的字段"
    if task.get("state") not in PLAN_EDITABLE_STATES:
        return False, f"状态 {task.get('state')} 下禁止编辑计划（执行中/审查中/DONE 受状态机门保护）"
    live = {x["id"]: x for x in roster()["roles"]}
    if "assignee" in fields:
        rid = (fields["assignee"] or "").strip()
        role = live.get(rid)
        if not role or role["ftype"] != "worker":
            return False, f"执行者必须是流程权限=执行的角色（{rid or '空'} 不合法）"
    if "reviewer" in fields:
        rid = (fields["reviewer"] or "").strip()
        if rid and (rid not in live or live[rid]["ftype"] != "reviewer"):
            return False, f"审查者必须是流程权限=审查的角色（{rid} 不合法）"
    if "verify_cmd" in fields:
        cmd = (fields["verify_cmd"] or "").strip()
        if not cmd:
            return False, "verify_cmd 不允许清空"
        if DENY_RE.search(cmd):
            return False, "verify_cmd 命中危险命令黑名单"
        if cmd.startswith("grep:") and len(cmd.split(":", 2)) != 3:
            return False, "grep: 格式应为 grep:相对路径:令牌1,令牌2"
    if not workspace_allowed(task.get("workspace", "")):
        return False, f"任务工作目录不在白名单 {ALLOWED_ROOTS}"
    changed = {}
    for k in ("title", "detail", "verify_cmd"):
        if k in fields:
            v = str(fields[k]).strip()
            if not v and k != "detail":
                return False, f"{k} 不允许为空"
            if len(v) > PLAN_FIELD_LIMITS[k]:
                return False, f"{k} 超长（上限 {PLAN_FIELD_LIMITS[k]}）"
            if task.get(k, "") != v:
                changed[k] = v
    for k in ("assignee", "reviewer"):
        if k in fields:
            v = (fields[k] or "").strip()
            if task.get(k, "") != v:
                changed[k] = v
    # DAG 依赖字段：after = 前置任务 id 列表（逗号分隔或 JSON 数组），空=无前置
    if "after" in fields:
        raw = (fields["after"] or "").strip()
        after_ids: list[str] = []
        if raw:
            if raw.startswith("["):
                try:
                    after_ids = [str(x).strip() for x in json.loads(raw) if str(x).strip()]
                except Exception:
                    return False, "after 必须是 JSON 数组（如 [\"T-001\",\"T-002\"]）或逗号分隔列表"
            else:
                after_ids = [x.strip() for x in raw.split(",") if x.strip()]
        # 校验：前置必须存在于同项目（或当前任务本身不允许——环检测交给调度器）
        existing = {x["id"] for x in t["tasks"]}
        unknown = [x for x in after_ids if x not in existing and x != task["id"]]
        if unknown:
            return False, f"after 引用了不存在的任务：{unknown}"
        if task["id"] in after_ids:
            return False, "after 不允许包含任务自身"
        if task.get("after", []) != after_ids:
            changed["after"] = after_ids
    new_order = None
    if "order" in fields:
        try:
            new_order = int(fields["order"])
        except (TypeError, ValueError):
            return False, "order 必须是整数"
    for k, v in changed.items():
        task[k] = v
    if new_order is not None:
        pid = task.get("project", "")
        idxs = [i for i, x in enumerate(t["tasks"]) if x.get("project") == pid]
        proj = [t["tasks"][i] for i in idxs]
        proj = [x for x in proj if x["id"] != task_id]
        pos = max(0, min(new_order, len(proj)))
        proj.insert(pos, task)
        for i, target in zip(idxs, proj):
            t["tasks"][i] = target
    save_task(task, t)
    fields_list = sorted(changed) + (['order'] if new_order is not None else [])
    audit(actor, "plan_updated", task_id,
          f"fields={fields_list} project={task.get('project', '—')}", assignee=task.get("assignee", ""),
          reviewer=task.get("reviewer", ""))
    return True, f"计划已更新：{', '.join(fields_list)}"


def page_plan_edit(tid):
    task, _ = get_task(tid)
    if not task:
        return page("错误", "/tasks", "<h3>任务不存在</h3>")
    if task.get("state") not in PLAN_EDITABLE_STATES:
        return page("编辑计划", "/tasks", f'<h2>⛔ 状态 {pill(task["state"])} 下禁止编辑</h2>'
                    f'<div class=card>仅 {" / ".join(sorted(PLAN_EDITABLE_STATES))} 状态可改计划。</div>'
                    f'<a class=btn href="/tasks/{tid}">返回任务详情</a>')
    r = roster()
    worker_opts = "".join(f'<option value="{x["id"]}{" selected" if x["id"] == task.get("assignee") else ""}>{x["id"]}（{x["duty"]}）</option>'
                          for x in r["roles"] if x["ftype"] == "worker")
    rev_opts = f'<option value="">—无—</option>' + "".join(f'<option value="{x["id"]}{" selected" if x["id"] == task.get("reviewer") else ""}>{x["id"]}（{x["duty"]}）</option>'
                                                            for x in r["roles"] if x["ftype"] == "reviewer")
    after_val = ",".join(task.get("after") or [])
    return page(f"编辑计划 {tid}", "/tasks", f"""
<h2>✏️ 编辑计划 · {tid}</h2>
<div class=card><p>状态：{pill(task["state"])} ｜ 项目：{task.get("project", "—")} ｜ 工作目录：<span class=mono>{task.get("workspace", "")}</span></p>
<p class=sub>可改：标题 / 规划目标 / 验收命令 / 执行者 / 审查者 / 顺序；不可改：任务ID、状态、项目归属、审计记录（append-only）。每次修改都会写入事件流，可在 /audit 与 /api/events 回放。</p></div>
<form method=post action="/tasks/{tid}/plan">
<div class=field><label>标题</label><input name=title value="{task.get("title", "")}" maxlength=200 required></div>
<div class=field><label>规划目标（detail）</label><textarea name=detail rows=5 style="width:100%;max-width:640px">{task.get("detail", "")}</textarea></div>
<div class=field><label>机器验收命令（危险命令黑名单强制）</label><input name=verify_cmd class=mono value="{task.get("verify_cmd", "")}" maxlength=500 required></div>
<div class=field><label>执行者（仅流程权限=执行）</label><select name=assignee required>{worker_opts}</select></div>
<div class=field><label>审查者（可空，仅流程权限=审查）</label><select name=reviewer>{rev_opts}</select></div>
<div class=field><label>计划顺序（项目内 0 起，可空=不调整）</label><input name=order style="max-width:120px" placeholder="如 2"></div>
<div class=field><label>前置依赖 after（逗号分隔任务ID，可空=无前置；环/脏引用由 DAG 调度器自动检出）</label><input name=after class=mono value="{after_val}" style="max-width:360px" placeholder="如 T-001,T-002"></div>
<input type=hidden name=actor value="web-edit">
<button class="btn primary" type=submit>💾 保存计划</button> <a class=btn href="/tasks/{tid}">取消</a>
</form>""")


# ---------------- 设计系统（ui-ux-pro-max 规范落地） ----------------

CSS = """
:root{--bg:#0b1220;--surface:#111a2c;--surface2:#16203a;--border:#1e293b;--text:#e2e8f0;--muted:#94a3b8;
--accent:#38bdf8;--ok:#34d399;--warn:#fbbf24;--danger:#f87171;--info:#a78bfa;--radius:12px}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.6 'Segoe UI','Microsoft YaHei',sans-serif}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:1180px;margin:0 auto;padding:20px 24px 60px}
header.top{position:sticky;top:0;z-index:20;background:rgba(11,18,32,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--border)}
.nav{max-width:1180px;margin:0 auto;display:flex;align-items:center;gap:6px;padding:10px 24px}
.brand{display:flex;align-items:center;gap:9px;font-weight:600;margin-right:18px}
.brand svg{color:var(--accent)}
.nav a{display:flex;align-items:center;gap:6px;padding:7px 12px;border-radius:8px;color:var(--muted);font-size:14px;transition:background .18s,color .18s}
.nav a:hover{background:var(--surface2);color:var(--text);text-decoration:none}
.nav a.on{background:var(--surface2);color:var(--accent)}
.spacer{flex:1}
h2{font-size:17px;margin:26px 0 12px;display:flex;align-items:center;gap:8px}
h2 svg{color:var(--accent)}
.grid{display:grid;gap:14px}
.g2{grid-template-columns:repeat(auto-fit,minmax(340px,1fr))}
.g3{grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:16px 18px;transition:border-color .18s,box-shadow .18s}
.card:hover{border-color:#2b3a55;box-shadow:0 4px 18px rgba(0,0,0,.25)}
.card h3{margin:0 0 10px;font-size:14px;color:var(--muted);font-weight:500;text-transform:uppercase;letter-spacing:.05em}
.metric{font-size:30px;font-weight:650;font-variant-numeric:tabular-nums}
.sub{color:var(--muted);font-size:13px;margin-top:4px}
table{width:100%;border-collapse:collapse;background:var(--surface);border-radius:var(--radius);overflow:hidden}
th{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;text-align:left;padding:9px 12px;border-bottom:1px solid var(--border);background:var(--surface2)}
td{padding:9px 12px;border-bottom:1px solid rgba(30,41,59,.6);font-size:14px;vertical-align:top}
tr:last-child td{border-bottom:none}tr:hover td{background:rgba(56,189,248,.04)}
.pill{display:inline-flex;align-items:center;gap:6px;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:500;border:1px solid}
.pill i{width:7px;height:7px;border-radius:50%;display:inline-block}
.p-ok{color:var(--ok);border-color:rgba(52,211,153,.35);background:rgba(52,211,153,.08)}.p-ok i{background:var(--ok)}
.p-warn{color:var(--warn);border-color:rgba(251,191,36,.35);background:rgba(251,191,36,.08)}.p-warn i{background:var(--warn)}
.p-bad{color:var(--danger);border-color:rgba(248,113,113,.35);background:rgba(248,113,113,.08)}.p-bad i{background:var(--danger)}
.p-info{color:var(--info);border-color:rgba(167,139,250,.35);background:rgba(167,139,250,.08)}.p-info i{background:var(--info)}
.btn{display:inline-flex;align-items:center;gap:5px;padding:6px 12px;border-radius:8px;border:1px solid var(--border);
background:var(--surface2);color:var(--text);font-size:13px;cursor:pointer;transition:background .18s,border-color .18s;text-decoration:none!important}
.btn:hover{background:#1c2942;border-color:#2b3a55}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#06121f;font-weight:600}
.btn.primary:hover{background:#7dd3fc}
.btn.danger{color:var(--danger);border-color:rgba(248,113,113,.4)}
.btn.danger:hover{background:rgba(248,113,113,.1)}
.btn.mini{padding:3px 9px;font-size:12px}
input,select,textarea{background:var(--surface2);border:1px solid var(--border);color:var(--text);border-radius:8px;
padding:8px 10px;font-size:14px;font-family:inherit;transition:border-color .18s}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(56,189,248,.15)}
label{display:block;color:var(--muted);font-size:12px;margin:10px 0 3px;letter-spacing:.03em}
input[type=text],input:not([type]),select{width:100%;max-width:460px}
.mono{font-family:Consolas,'JetBrains Mono',monospace;font-size:13px}
.bar{height:8px;background:var(--surface2);border-radius:99px;overflow:hidden;margin:6px 0 4px}
.bar>i{display:block;height:100%;background:linear-gradient(90deg,var(--accent),var(--info));border-radius:99px;transition:width .3s}
.plan-list{display:flex;flex-direction:column;gap:12px}.wave-list{display:flex;flex-direction:column;gap:12px}.plan{padding:18px}.plan-head{display:flex;justify-content:space-between;gap:24px;align-items:center}.plan-summary{min-width:280px}.plan-task{border:1px solid var(--border);border-radius:9px;background:var(--surface2);overflow:hidden}.plan-task summary{display:flex;align-items:center;gap:10px;padding:11px 14px;cursor:pointer;list-style:none}.plan-task summary::-webkit-details-marker{display:none}.plan-task summary:hover{background:#1c2942}.plan-state{min-width:100px}.plan-percent{margin-left:auto;color:var(--accent);font-variant-numeric:tabular-nums}.plan-detail{padding:4px 18px 15px;border-top:1px solid var(--border)}
@media(max-width:650px){.plan-head{display:block}.plan-summary{min-width:0;margin-top:12px}.plan-task summary{flex-wrap:wrap}.plan-percent{margin-left:0}}
pre{background:#0a101d;border:1px solid var(--border);border-radius:8px;padding:12px;overflow:auto;max-width:100%;font-size:12.5px;line-height:1.5;color:#cbd5e1}
form.inline{display:inline}
.field{margin-bottom:4px}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
"""

ICON = {
    "logo": '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/></svg>',
    "dash": '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
    "users": '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/></svg>',
    "proj": '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>',
    "tasks": '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="6" height="6" rx="1"/><path d="m3 17 2 2 4-4"/><path d="M13 6h8M13 12h8M13 18h8"/></svg>',
    "audit": '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/></svg>',
}

STATE_PILL = {"DONE": "p-ok", "PASS": "p-ok", "online": "p-ok", "SUCCEEDED": "p-ok",
              "DOING": "p-info", "ASSIGNED": "p-info", "REVIEWING": "p-info", "SUBMITTED": "p-info",
              "REWORK": "p-warn", "PARTIAL": "p-warn", "degraded": "p-warn", "edited(建议烟测)": "p-warn",
              "BLOCKED": "p-bad", "FAILED": "p-bad", "offline": "p-bad", "DRAFT": "p-info"}


def pill(text):
    cls = STATE_PILL.get(text, "p-info")
    return f'<span class="pill {cls}"><i></i>{text}</span>'


def page(title, active, body):
    nav_items = [("/", "dash", "总览"), ("/projects", "proj", "项目"), ("/roles", "users", "角色"),
                 ("/tasks", "tasks", "任务"), ("/audit", "audit", "审计")]
    nav = "".join(f'<a href="{href}" class="{"on" if href == active else ""}">{ICON[ic]}{label}</a>'
                  for href, ic, label in nav_items)
    return (f'<!doctype html><html lang=zh><head><meta charset=utf-8>'
            f'<meta name=viewport content="width=device-width,initial-scale=1">'
            f'<title>{title} · Fleet 控制台</title><style>{CSS}</style></head><body>'
            f'<header class=top><div class=nav><span class=brand>{ICON["logo"]}AideanAgentFleet</span>'
            f'{nav}<span class=spacer></span>'
            f'<form class=inline method=post action=/fleet/start><button class="btn mini primary" type=submit>启动舰队</button></form>'
            f'</div></header><div class=wrap>{body}</div></body></html>')


def fmt_dur(m):
    if m is None or m == "—":
        return "—"
    m = float(m)
    return f"{m:.0f} 分钟" if m < 90 else f"{m/60:.1f} 小时"


def page_dashboard():
    h = fleet_health()
    ok_n = sum(1 for _, v in h["checks"] if v)
    checks = "".join(f'<tr><td>{k}</td><td>{pill("online" if v else "FAILED")}</td></tr>' for k, v in h["checks"])
    projs = "".join(project_card(m) for m in (project_metrics(x["pid"]) for x in projects()["projects"]) if m)
    roles = roster()["roles"]
    rrows = "".join(f'<tr><td class=mono>{x["id"]}</td><td>{x["duty"]}</td><td>{pill(x["ftype"])}</td>'
                    f'<td class=mono>{x["model"]["model_id"]}</td><td>{pill(x["status"])}</td></tr>' for x in roles)
    body = f"""
<div class=grid g3 style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr))">
 <div class=card><h3>健康检查</h3><div class="metric {'metric' if ok_n==len(h['checks']) else ''}" style="color:{'var(--ok)' if ok_n==len(h['checks']) else 'var(--warn)'}">{ok_n}/{len(h['checks'])}</div><div class=sub>四条件自检通过项</div></div>
 <div class=card><h3>角色</h3><div class=metric>{len(roles)}</div><div class=sub>+ Manager(9900, agnes-3.0-flash)</div></div>
 <div class=card><h3>项目 / 任务</h3><div class=metric>{len(projects()['projects'])} <span style="font-size:16px;color:var(--muted)">/ {len(tasks()['tasks'])}</span></div><div class=sub>项目数 / 任务数</div></div>
</div>
<h2>{ICON["proj"]}项目进度</h2>
<div class=grid class=g2 style="display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr))">{projs or '<div class=card><div class=sub>暂无项目——在「任务」页新建任务时填写项目名即可自动建项。</div></div>'}</div>
<h2>{ICON["users"]}角色在线</h2>
<table><tr><th>ID</th><th>职能</th><th>流程权限</th><th>模型</th><th>状态</th></tr>{rrows}</table>
<details style="margin-top:18px"><summary style="cursor:pointer;color:var(--muted)">健康检查明细（点击展开）</summary>
<table style="margin-top:8px">{checks}</table></details>"""
    return page("总览", "/", body)


def project_card(m):
    tk = "".join(f'<span class="pill p-info" style="margin:2px">{k}:{v}</span>'
                 for k, v in sorted(m["states"].items()))
    rt = "".join(f'<tr><td class=mono>{rid}</td><td class=mono>{v["tokens"]:,} tok(估)</td>'
                 f'<td>{v["convs"]} 轮</td></tr>' for rid, v in m["role_tokens"].items()) or \
         '<tr><td colspan=3 class=sub>暂无 A2A 会话数据</td></tr>'
    eta = (f"预计还需 {fmt_dur(m['eta_min'])} · 约 {m['eta_at']} 完成" if m["eta_min"] is not None
           else "完成全部任务后可估算 ETA")
    return f"""<div class=card><h3>{m['name']}</h3>
<div class=metric>{m['progress']}%</div><div class=bar><i style="width:{m['progress']}%"></i></div>
<div class=sub>{m['done']}/{m['total']} 任务完成 · 状态：{tk or '—'}</div>
<div class=sub>整体耗时：{fmt_dur(m['elapsed_min'])} ｜ 平均任务：{fmt_dur(m['avg_task_min'])}</div>
<div class=sub>{eta}</div>
<details style="margin-top:8px"><summary style="cursor:pointer;font-size:13px;color:var(--accent)">按角色 token 消耗（估算）</summary>
<table style="margin-top:6px"><tr><th>角色</th><th>token(估)</th><th>会话轮</th></tr>{rt}</table>
<div class=sub>估算口径：a2a_conversations 实际文本量 ÷ {CHARS_PER_TOKEN}（中英混合系数）</div></details></div>"""


def plan_task_row(task):
    state = task.get("state", "DRAFT")
    weight = round(STATE_WEIGHT.get(state, 0) * 100)
    return (f'<details class="plan-task"><summary><span class="plan-state">{pill(state)}</span>'
            f'<strong>{task["id"]}</strong> {task.get("title", "未命名任务")}'
            f'<span class="plan-percent">{weight}%</span></summary>'
            f'<div class="plan-detail"><div class="bar"><i style="width:{weight}%"></i></div>'
            f'<p><b>执行者：</b>{task.get("assignee", "—")}　<b>审查者：</b>{task.get("reviewer") or "—"}</p>'
            f'<p><b>规划目标：</b>{task.get("detail") or "未填写"}</p>'
            f'<p><b>验收标准：</b><span class="mono">{task.get("verify_cmd") or "未填写"}</span></p>'
            f'<p><b>当前说明：</b>{task.get("state_note") or "暂无"}　<b>返工：</b>{task.get("rework_count", 0)} 次</p>'
            f'<a class="btn mini" href="/tasks/{task["id"]}">打开任务详情</a> '
            + (f'<a class="btn mini" href="/tasks/{task["id"]}/plan-edit">✏️ 编辑计划</a>'
               if task.get("state") in PLAN_EDITABLE_STATES else "") + '</div></details>')


def project_plan(pid):
    metric = project_metrics(pid)
    if not metric:
        return ""
    project_tasks = [x for x in tasks()["tasks"] if x.get("project") == pid]
    rows = "".join(plan_task_row(x) for x in project_tasks) or '<div class="sub">暂无任务计划。</div>'
    return (f'<section class="plan card" data-pid="{pid}"><div class="plan-head"><div><h3>整体任务计划</h3>'
            f'<div class="metric">{metric["progress"]}%</div><div class="sub">已完成 {metric["done"]} / 共 {metric["total"]} 项，剩余 {metric["total"] - metric["done"]} 项</div></div>'
            f'<div class="plan-summary"><div class="bar"><i style="width:{metric["progress"]}%"></i></div>'
            f'<span>整体完成百分比：{metric["progress"]}%</span></div></div>{rows}</section>')


def page_projects():
    cards = "".join(project_card(m) for m in (project_metrics(x["pid"]) for x in projects()["projects"]) if m)
    plans = "".join(project_plan(x["pid"]) for x in projects()["projects"])
    waves = "".join(project_ready_wave(x["pid"]) for x in projects()["projects"])
    return page("项目", "/projects", f"""
<h2>{ICON["proj"]}项目看板</h2>
<div class=grid style="display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr))">{cards or '<div class=card><div class=sub>暂无项目。</div></div>'}</div>
<h2>{ICON["tasks"]}完整任务计划</h2>
<div class="plan-list">{plans or '<div class=card><div class=sub>暂无任务计划。</div></div>'}</div>
<h2>{ICON["proj"]}推荐波（DAG 调度器）</h2>
<div class="wave-list">{waves or '<div class=card><div class=sub>暂无项目。</div></div>'}</div>
<p class=sub style="max-width:760px">进度会根据任务状态实时计算；任务计划允许动态变更。点击每项计划即可展开目标、执行者、审查者、验收标准和当前说明。</p>
<p class=sub style="max-width:760px">推荐波：依赖已满足且角色无在途任务（ASSIGNED/DOING/SUBMITTED/REVIEWING）的 DRAFT/REWORK 任务。调度器只推荐、不自动派工——点击「派工」走任务详情的 dispatch 完整拦截链（离线/依赖/状态机）。每角色 1 并发。本页 15s 轮询 /api/ready-wave。</p>
<script src="/static/js/plan-sync-client.js"></script>
<script>
FleetPlanSync.start();
/* 推荐波轮询：与 FleetPlanSync 互不影响，失败指数退避（2s→60s 封顶） */
(function () {{
  "use strict";
  var INTERVAL = 15000, MAX_BACKOFF = 60000, attempts = 0;
  var pids = Array.prototype.map.call(
    document.querySelectorAll(".wave-list .wave[data-pid]"), function (el) {{
      return el.getAttribute("data-pid");
    }});
  if (!pids.length) return;
  function tick() {{
    pids.forEach(function (pid) {{
      fetch("/api/ready-wave?project=" + encodeURIComponent(pid), {{ credentials: "same-origin" }})
        .then(function (r) {{
          if (!r.ok) throw new Error("HTTP " + r.status);
          return r.json();
        }}).then(function (w) {{ paint(pid, w); attempts = 0; }})
        .catch(function () {{ attempts += 1; }});
    }});
    var backoff = Math.min(MAX_BACKOFF, 2000 * Math.pow(2, attempts));
    setTimeout(tick, attempts ? backoff : INTERVAL);
  }}
  function paint(pid, w) {{
    var host = document.querySelector(".wave-list .wave[data-pid=\"" + pid + "\"]");
    if (!host || !w || !w.scheduler_ok) return;
    var rows = (w.ready || []).map(function (r) {{
      return "<tr><td class=mono><a href=/tasks/" + r.id + ">" + r.id + "</a></td>" +
        "<td>" + String(r.title || "—").slice(0, 40) + "</td>" +
        "<td class=mono>" + (r.assignee || "—") + "</td>" +
        "<td class=mono>" + ((r.after || []).join("、") || "—") + "</td>" +
        "<td><form class=inline method=post action=/tasks/" + r.id + "/dispatch>" +
        "<button class=\"btn mini primary\">派工</button></form></td></tr>";
    }}).join("");
    var blk = Object.keys(w.blocked || {{}}).map(function (id) {{
      return id + "：" + w.blocked[id];
    }}).join("；");
    var body = "<table><tr><th>ID</th><th>标题</th><th>执行者</th><th>前置</th><th>操作</th></tr>" +
      (rows || "<tr><td colspan=5 class=sub>无推荐任务</td></tr>") + "</table>";
    if (blk) body += "<div class=sub>被拦截：" + blk + "</div>";
    if ((w.in_flight || []).length) body += "<div class=sub>角色在途：" + w.in_flight.join("、") + "</div>";
    if ((w.invalid || []).length) body += "<div class=sub style=color:#e08c8c>依赖数据异常：" + w.invalid.join("、") + "</div>";
    host.innerHTML = "<b>" + pid + "</b>：推荐 " + (w.ready || []).length +
      " ｜ 拦截 " + Object.keys(w.blocked || {{}}).length +
      " ｜ 在途 " + (w.in_flight || []).length + " " + body;
  }}
  setTimeout(tick, 1000);
}})();
</script>""")


def project_ready_wave(pid):
    """项目看板「推荐波」区块：ready 带派工按钮 / blocked 列原因 / in_flight 只读。"""
    if not SCHEDULER_OK:
        return (f'<div class=card><b>{pid}</b>：调度器不可用（dispatcher/scheduler.py 缺失），'
                f'<a class=mono href="/api/ready-wave?project={pid}">API 降级</a></div>')
    w = ready_wave(pid)
    if not w:
        return f'<div class=card><b>{pid}</b>：无项目数据</div>'
    rows = ""
    for r in w["ready"]:
        rows += (f'<tr><td class=mono><a href=/tasks/{r["id"]}>{r["id"]}</a></td>'
                 f'<td>{r["title"][:40] or "—"}</td><td class=mono>{r["assignee"]}</td>'
                 f'<td class=mono>{",".join(r["after"]) or "—"}</td>'
                 f'<td><form class=inline method=post action=/tasks/{r["id"]}/dispatch>'
                 f'<button class="btn mini primary">派工</button></form></td></tr>')
    blk = "".join(f'<div class=sub>{bid}：{reason}</div>' for bid, reason in w["blocked"].items())
    inft = "".join(f'<div class=sub>{tid}</div>' for tid in w["in_flight"])
    invalid = "".join(f'<div class=sub>{tid}：after 引用不存在或依赖环</div>' for tid in w["invalid"])
    body = (f'<table><tr><th>ID</th><th>标题</th><th>执行者</th><th>前置</th><th>操作</th></tr>{rows or "<tr><td colspan=5 class=sub>无推荐任务</td></tr>"}'
           f'</table>')
    if blk:
        body += f'<div class=sub>被拦截：{blk}</div>'
    if inft:
        body += f'<div class=sub>角色在途（占并发位）：{inft}</div>'
    if invalid:
        body += f'<div class=sub style=color:#e08c8c>依赖数据异常：{invalid}</div>'
    return f'<div class=wave card data-pid="{pid}"><b>{pid}</b>：推荐 {len(w["ready"])} ｜ 拦截 {len(w["blocked"])} ｜ 在途 {len(w["in_flight"])}</div>{body}'


def page_roles():
    rows = ""
    for x in roster()["roles"]:
        st = port_listening(x["port"])
        status = x["status"] if st else "offline"
        tk = role_token_stats(x["id"])
        rows += f"""<tr><td class=mono>{x['id']}</td><td><b>{x['duty']}</b><div class=sub class=mono>名片:{x['card']} · :{x['port']}</div></td>
<td>{pill(x['ftype'])}</td><td class=mono>{x['model']['base_url']}<br><b>{x['model']['model_id']}</b>{'<br><span class=sub>proxy:'+x['model']['proxy']+'</span>' if x['model'].get('proxy') else ''}</td>
<td class=mono>{tk['tokens_est']:,}<div class=sub>{tk['conversations']} 轮会话(估)</div></td>
<td>{pill(status)}</td>
<td><a class="btn mini" href=/roles/{x['id']}/start>启动</a> <a class="btn mini" href=/roles/{x['id']}/smoke title=连通测试：发一条消息验证模型/密钥/配置可用>连通测试</a>
<a class="btn mini gray" href=/roles/{x['id']}/stop>停止</a> <a class="btn mini" href=/roles/{x['id']}/edit>编辑</a>
<form class=inline method=post action=/roles/{x['id']}/delete onsubmit="return confirm('确认删除角色 {x['id']}？将删除 profile 并同步清理通讯录')"><button class="btn mini danger">删除</button></form></td></tr>"""
    ftype_labels = {"worker": "执行（写代码/产出物）", "reviewer": "审查（只审不改）", "observer": "观察（只读）"}
    ftype_opts = "".join(f'<option value="{t}">{ftype_labels[t]}</option>' for t in FLOW_TYPES)
    return page("角色", "/roles", f"""
<div style="display:flex;align-items:center;gap:12px"><h2 style="margin:26px 0 12px">{ICON["users"]}角色名册（{len(roster()['roles'])}）</h2>
<form class=inline method=post action=/roles/common-config><button class="btn mini" title="为全部角色写入通用基座：保留联网/查询/文件/终端，裁剪重型工具集">通用基座配置→全员应用</button></form></div>
<table><tr><th>ID</th><th>职能 / 名片</th><th>流程权限</th><th>模型</th><th>token 消耗(估)</th><th>状态</th><th>操作</th></tr>{rows}</table>
<p class=sub style="max-width:820px">「职能名称」自由填写（前端开发/营销/客服…），决定 SOUL 人设与展示；「流程权限」固定三选一，决定它能否派工/送审——这是流程正确性的保证。烟测=连通测试：向该角色发一条消息并期待"就绪"，验证模型ID/密钥/配置真实可用（源自硬件上电"冒烟测试"术语）。</p>
<h2>新增角色</h2>
<form method=post action=/roles/add>
<div class=field><label>角色ID（小写英文，如 kefu-1 / marketing-2）</label><input name=id required></div>
<div class=field><label>职能名称（自由填写，如：客服专员）</label><input name=duty required></div>
<div class=field><label>流程权限（决定它在这个流程里能做什么，不可自由填写）</label><select name=ftype>{ftype_opts}</select></div>
<div class=field><label>名片名（Agent Card 显示，如 Kefu-1）</label><input name=card></div>
<div class=field><label>工作目录白名单（执行类角色建议填写）</label><input name=workspace placeholder="E:\\Demo\\Test0912"></div>
<div class=field><label>模型 base_url</label><input name=base_url required></div>
<div class=field><label>模型 ID</label><input name=model_id required></div>
<div class=field><label>API Key（只写入该角色 .env，不进配置文件）</label><input name=api_key required></div>
<div class=field><label>代理（可空；如 http://127.0.0.1:10808）</label><input name=proxy></div>
<button class="btn primary" type=submit>➕ 创建角色</button></form>""")


def page_role_edit(rid):
    r = roster()
    role = next((x for x in r["roles"] if x["id"] == rid), None)
    if not role:
        return page("错误", "/roles", "<h3>角色不存在</h3>")
    m = role["model"]
    return page("编辑角色", "/roles", f"""
<h2>编辑角色 {role['id']}</h2>
<form method=post action=/roles/edit>
<input type=hidden name=id value="{rid}">
<div class=field><label>职能名称</label><input name=duty value="{role['duty']}"></div>
<div class=field><label>名片名</label><input name=card value="{role['card']}"></div>
<div class=field><label>工作目录白名单</label><input name=workspace value="{role.get('workspace','')}"></div>
<div class=field><label>模型 base_url</label><input name=base_url value="{m['base_url']}"></div>
<div class=field><label>模型 ID</label><input name=model_id value="{m['model_id']}"></div>
<div class=field><label>API Key（留空=不修改）</label><input name=api_key placeholder="留空保持现有 Key"></div>
<div class=field><label>代理（清空=取消代理）</label><input name=proxy value="{m.get('proxy','')}"></div>
<button class="btn primary" type=submit>保存修改</button> <a class=btn href=/roles>取消</a>
</form><p class=sub>流程权限（worker/reviewer/observer）创建后不可改——它决定流程中的权限边界；如需变更请删除重建。</p>""")


def page_tasks():
    rows = "".join(f'<tr><td class=mono><a href=/tasks/{x["id"]}>{x["id"]}</a></td><td>{x["title"][:40]}</td>'
                   f'<td>{x.get("project","—")}</td><td class=mono>{x["assignee"]}</td><td>{x.get("reviewer","—")}</td>'
                   f'<td>{pill(x["state"])}</td><td>{x.get("rework_count",0)}</td></tr>' for x in reversed(tasks()["tasks"]))
    r = roster()
    worker_opts = "".join(f'<option value={x["id"]}>{x["id"]}（{x["duty"]}）</option>' for x in r["roles"] if x["ftype"] == "worker")
    rev_opts = "".join(f'<option value={x["id"]}>{x["id"]}（{x["duty"]}）</option>' for x in r["roles"] if x["ftype"] == "reviewer")
    proj_opts = "".join(f'<option value={x["pid"]}>{x["name"]}</option>' for x in projects()["projects"])
    return page("任务", "/tasks", f"""
<h2>任务板</h2>
<table><tr><th>ID</th><th>标题</th><th>项目</th><th>执行者</th><th>审查者</th><th>状态</th><th>返工</th></tr>{rows}</table>
<h2>新建任务</h2>
<form method=post action=/tasks/add>
<div class=field><label>标题</label><input name=title required></div>
<div class=field><label>所属项目（已有）</label><select name=project><option value="">—不归属—</option>{proj_opts}</select></div>
<div class=field><label>或新建项目名（留空项目下拉则忽略）</label><input name=new_project placeholder="如：Test0912-贪吃蛇"></div>
<div class=field><label>执行者（仅流程权限=执行 的角色）</label><select name=assignee required>{worker_opts}</select></div>
<div class=field><label>审查者（可空）</label><select name=reviewer><option value="">—无—</option>{rev_opts}</select></div>
<div class=field><label>工作目录（白名单内）</label><input name=workspace required></div>
<div class=field><label>目标与约束详情</label><textarea name=detail rows=4 style="width:100%;max-width:640px"></textarea></div>
<div class=field><label>机器验收命令（grep:相对路径:令牌1,令牌2 　或　ASCII 安全命令；退出码判定 PASS）</label><input name=verify_cmd required style="width:100%;max-width:640px" class=mono></div>
<button class="btn primary" type=submit>➕ 建任务</button></form>""")


def page_task_detail(tid):
    task, _ = get_task(tid)
    if not task:
        return page("任务", "/tasks", "<h3>任务不存在</h3>")
    hist = "".join(f'<tr><td class=mono>{h["ts"]}</td><td>{h["from"]} → {h["to"]}</td><td>{h["actor"]}</td><td>{h["detail"][:90]}</td></tr>'
                   for h in task.get("history", []))
    btns = ""
    if task["state"] in ("DRAFT", "REWORK", "PARTIAL", "FAILED"):
        btns += f'<form class=inline method=post action=/tasks/{tid}/dispatch><button class="btn primary">📤 派工（经Manager）</button></form> '
    if task["state"] in ("SUBMITTED", "REVIEWING", "REWORK"):
        btns += f'<form class=inline method=post action=/tasks/{tid}/verify><button class=btn>🤖 机器验收</button></form> '
    if task["state"] in ("SUBMITTED", "REVIEWING") and task.get("verify_ok"):
        btns += f'<form class=inline method=post action=/tasks/{tid}/review><button class=btn>⚖️ 送审（{task.get("reviewer") or "未指定"}）</button></form> '
    if task["state"] in ("REVIEWING", "PARTIAL", "BLOCKED"):
        btns += f'<form class=inline method=post action=/tasks/{tid}/rework><input name=reason placeholder=返工原因 style="width:180px"><button class="btn danger">🔁 判返工</button></form> '
        btns += f'<form class=inline method=post action=/tasks/{tid}/close><input name=note placeholder=收口备注 style="width:180px"><button class=btn>✅ 收口DONE</button></form>'
    if task["state"] == "FAILED":
        btns += f'<form class=inline method=post action=/tasks/{tid}/close><input name=note placeholder=收口备注 style="width:180px"><button class=btn>✅ 收口DONE</button></form>'
    if task["state"] in PLAN_EDITABLE_STATES:
        btns += f'<a class="btn mini" href="/tasks/{tid}/plan-edit">✏️ 编辑计划</a> '
    ev = f'<p>机器验收：{pill("online" if task.get("verify_ok") else "FAILED")} 证据：{task.get("evidence","—")}</p>'
    live_ids = {x["id"] for x in roster()["roles"]}
    retired_badge_a = pill("已退役") if task["assignee"] not in live_ids else ""
    retired_badge_r = pill("已退役") if task.get("reviewer") and task["reviewer"] not in live_ids else ""
    return page(tid, "/tasks", f"""
<h2>{tid} · {task['title']}</h2>
<div class=card><p>状态：{pill(task['state'])} ｜ 执行者：<span class=mono>{task['assignee']}</span>{retired_badge_a} ｜ 审查者：<span class=mono>{task.get("reviewer") or "—"}</span>{retired_badge_r} ｜ 返工：{task.get("rework_count",0)} 次 ｜ 项目：{task.get("project","—")}　{task.get("state_note","")}</p>
{f'<div class="card" style="border-color:rgba(251,191,36,.4)"><b>⚠ 历史任务说明：</b>{task.get("retired_note","")}</div>' if task.get("retired_note") else ""}
{ev}<div>{btns}</div></div>
<h2>员工回执</h2><pre>{(task.get('report') or '（未派工或未回执）')[:4000]}</pre>
<h2>审查判定</h2><pre>{(task.get('review_report') or '（未送审）')[:3000]}</pre>
<h2>流转历史</h2><table><tr><th>时间</th><th>迁移</th><th>操作者</th><th>说明</th></tr>{hist}</table>
<p class=sub>页面每 15 秒自动刷新 <meta http-equiv=refresh content=15></p>""")


def model_provider(model_id, base_url=""):
    value = f"{model_id} {base_url}".lower()
    providers = (("sensenova", "sensenova"), ("modelscope", "modelscope"),
                 ("qwen", "阿里云/通义"), ("deepseek", "deepseek"),
                 ("openrouter", "openrouter"), ("agnes", "agnes"),
                 ("nvidia", "nvidia"))
    return next((label for token, label in providers if token in value), "custom")


def completion_evaluation(task):
    state = task.get("state")
    retries = task.get("rework_count", 0)
    if state == "DONE" and task.get("verify_ok") and retries == 0:
        return "圆满完成无返工"
    if state == "DONE":
        return "完成有返工"
    if state in ("PARTIAL", "FAILED"):
        return "部分完成有缺口"
    if state in ("BLOCKED",):
        return "受阻未产出"
    return "未派工"


def completion_report(project_id, closed_task=None):
    project = next((x for x in projects()["projects"] if x["pid"] == project_id), None)
    if not project:
        return None
    all_tasks = [x for x in tasks()["tasks"] if x.get("project") == project_id]
    if closed_task and closed_task not in all_tasks:
        all_tasks.append(closed_task)
    roles = {x["id"]: x for x in roster()["roles"]}
    rows = []
    manager_tasks = [x for x in all_tasks if x.get("manager_task")]
    for task in all_tasks:
        role = roles.get(task.get("assignee"), {})
        model = role.get("model", {})
        rows.append((role.get("duty", task.get("assignee", "未知")),
                     model_provider(model.get("model_id", ""), model.get("base_url", "")),
                     model.get("model_id", "未知"), task.get("title", ""), completion_evaluation(task)))
    for task in manager_tasks:
        rows.append(("Manager", "Hermes", "agnes-3.0-flash", task.get("title", "总调度"), completion_evaluation(task)))
    lines = [f"# {project['name']} 完成度报告", "", f"生成时间：{now()}", "",
             "## 完成度明细", "", "| 角色 | 模型提供商 | 模型 | 任务 | 评价 |",
             "|---|---|---|---|---|"]
    lines.extend(f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in rows)
    lines += ["", "## 判定依据", "", "评价依据任务最终状态、机器门结果和返工次数；未完成任务不会被标记为圆满完成。"]
    path = FLEET / "reports" / f"{project_id}-completion-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def page_audit():
    lines = AUDIT_FILE.read_text(encoding="utf-8").splitlines()[-200:] if AUDIT_FILE.exists() else []
    rows = ""
    for l in reversed(lines):
        try:
            d = json.loads(l)
            rows += f'<tr><td class=mono>{d["ts"]}</td><td>{d["actor"]}</td><td>{d["action"]}</td><td class=mono>{d["task"]}</td><td>{d["detail"][:110]}</td></tr>'
        except Exception:
            continue
    return page("审计", "/audit", f'<h2>审计日志（最近 200 条，append-only）</h2><table><tr><th>时间</th><th>谁</th><th>动作</th><th>任务</th><th>详情</th></tr>{rows}</table>')


def fleet_health():
    r = roster()
    checks = []
    ok, out = hermes("--version", 30)
    checks.append(("hermes 可用 (v0.21.1)", ok and "v0.21.1" in out))
    checks.append(("Manager 名片 9900=Hermes-Manager", card_name(9900) == "Hermes-Manager"))
    for x in r["roles"]:
        checks.append((f"{x['id']} 网关:{x['port']}", port_listening(x["port"])))
        checks.append((f"{x['id']} 名片={x['card']}", card_name(x["port"]) == x["card"]))
    ok, out = hermes("tools list", 60)
    checks.append(("a2a 工具已启用", "enabled  a2a" in out.replace("✓ enabled", "enabled")))
    checks.append(("审计日志在写", AUDIT_FILE.exists() and AUDIT_FILE.stat().st_size > 0))
    integ = integrity_report()
    checks.append(("任务完整性（无伪造DONE）", not integ["fail"]))
    return {"version": CONSOLE_VERSION, "checks": checks, "roles": len(r["roles"]),
            "tasks": len(tasks()["tasks"]), "roots": ALLOWED_ROOTS,
            "audit_chain": audit_chain(),
            "integrity_fail": integ["fail"], "integrity_issues": integ["issues"],
            "launch_routes": ["/api/launch-event", "/api/launch-resolve"]}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _html(self, body, code=200):
        b = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _redirect(self, to="/"):
        self.send_response(303)
        self.send_header("Location", to)
        self.end_headers()

    def _sse_write(self, payload):
        """写一帧 SSE（默认 message 事件）并立即 flush；客户端断开时抛 ConnectionError 由上层收尾。"""
        self.wfile.write(f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8"))
        self.wfile.flush()

    _STATIC_MIME = {".js": "application/javascript; charset=utf-8",
                    ".css": "text/css; charset=utf-8",
                    ".html": "text/html; charset=utf-8",
                    ".json": "application/json; charset=utf-8",
                    ".svg": "image/svg+xml", ".png": "image/png",
                    ".ico": "image/x-icon", ".map": "application/json"}

    def _static(self, path):
        """GET /static/<rel>：只读服务 STATIC_DIR 下的资源；越界/目录/不存在一律 404。"""
        rel = unquote(path[len("/static/"):]).replace("\\", "/")
        f = (STATIC_DIR / rel).resolve() if rel and ".." not in rel else None
        if f is None or not f.is_file():
            return self._html(page("404", "/", "<h3>404</h3>"), 404)
        try:
            f = f.relative_to(STATIC_DIR.resolve())
        except ValueError:
            return self._html(page("404", "/", "<h3>404</h3>"), 404)
        full = STATIC_DIR.resolve() / f
        data = full.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", self._STATIC_MIME.get(f.suffix.lower(),
                                                               "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _stream(self, q):
        """GET /api/stream?project=<pid>：SSE 长连接（G2）。
        增量监听 audit.log 新行，按项目过滤后以 message 帧推送（形状同 /api/events 单条）；
        无新事件时每 STREAM_HEARTBEAT_SEC（15s）发 SSE 注释心跳 ':hb'，保活并触发前端重连计时。"""
        pid = (q.get("project") or [""])[0].strip()
        if not pid:
            return self._json({"error": "缺少 project 参数"}, 400)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            lines = AUDIT_FILE.read_text(encoding="utf-8").splitlines() if AUDIT_FILE.exists() else []
        except OSError:
            lines = []
        cursor = len(lines)  # 从建连时刻起只推增量
        task_project = {x["id"]: x.get("project", "") for x in tasks()["tasks"]}
        last_beat = time.time()
        self._sse_write({"hello": True, "project": pid, "seq": cursor})
        try:
            while True:
                time.sleep(0.5)
                try:
                    new_lines = AUDIT_FILE.read_text(encoding="utf-8").splitlines()[cursor:] \
                        if AUDIT_FILE.exists() else []
                except OSError:
                    new_lines = []
                if new_lines:
                    for offset, l in enumerate(new_lines, 1):
                        seq = cursor + offset
                        try:
                            d = json.loads(l)
                        except Exception:
                            continue
                        tid = d.get("task", "")
                        if task_project.get(tid, "") != pid:
                            continue
                        self._sse_write({"seq": seq, "timestamp": d.get("ts", ""),
                                         "actor": d.get("actor", ""), "action": d.get("action", ""),
                                         "taskId": tid, "from": d.get("from", ""),
                                         "to": d.get("to", ""),
                                         "assignee": d.get("assignee", ""),
                                         "reviewer": d.get("reviewer", ""),
                                         "summary": _redact(d.get("detail", "")),
                                         "url": d.get("url") or task_event_url(
                                             task_id=tid, project_id=pid)})
                    cursor += len(new_lines)
                    last_beat = time.time()
                elif time.time() - last_beat >= STREAM_HEARTBEAT_SEC:
                    self.wfile.write(b": hb\n\n")
                    self.wfile.flush()
                    last_beat = time.time()
        except (BrokenPipeError, ConnectionError, ConnectionResetError, OSError):
            pass  # 客户端断开：正常收尾
        except Exception:
            pass

    def _form(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n)
        s = None
        for enc in ("utf-8", "gbk"):
            try:
                s = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if s is None:
            s = raw.decode("utf-8", errors="replace")
        return {k: v[0] for k, v in parse_qs(s, keep_blank_values=True).items()}

    def _require_token(self):
        """R6 写操作鉴权：FLEET_API_TOKEN 为空=本机模式直接放行；否则需要 Bearer。"""
        if not FLEET_API_TOKEN:
            return True
        auth = (self.headers.get("Authorization") or "").strip()
        import hmac as _hmac
        if not _hmac.compare_digest(auth, f"Bearer {FLEET_API_TOKEN}"):
            self._json({"ok": False, "error": "unauthorized: missing/invalid Bearer token"}, 401)
            return False
        return True

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self._html(page_dashboard())
        elif path == "/projects":
            self._html(page_projects())
        elif path == "/roles":
            self._html(page_roles())
        elif path.startswith("/roles/") and path.endswith("/smoke"):
            rid = path.split("/")[2]
            smoke_role(rid)
            self._redirect("/roles")
        elif path.startswith("/roles/") and path.endswith("/start"):
            ok, msg = start_role(path.split("/")[2])
            audit("console", "role_start", path.split("/")[2], msg)
            self._redirect("/roles")
        elif path.startswith("/roles/") and path.endswith("/stop"):
            stop_role(path.split("/")[2])
            self._redirect("/roles")
        elif path.startswith("/roles/") and path.endswith("/edit"):
            self._html(page_role_edit(path.split("/")[2]))
        elif path == "/tasks":
            self._html(page_tasks())
        elif path.startswith("/tasks/") and path.endswith("/plan-edit"):
            self._html(page_plan_edit(path.split("/")[2]))
        elif path.startswith("/tasks/"):
            self._html(page_task_detail(path.split("/")[2]))
        elif path == "/audit":
            self._html(page_audit())
        elif path.startswith("/reports/"):
            report = FLEET / "reports" / Path(path.split("/", 2)[2]).name
            if not report.exists():
                self._html(page("404", "/", "<h3>报告不存在</h3>"), 404)
            else:
                self._html(page(report.stem, "/audit", f"<h2>{report.name}</h2><pre>{report.read_text(encoding='utf-8')}</pre>"))
        elif path == "/api/health":
            self._json(fleet_health())
        elif path == "/api/audit-chain":
            try:
                import sys as _sys4
                if str(FLEET / "console") not in _sys4.path:
                    _sys4.path.insert(0, str(FLEET / "console"))
                from services import verify_audit_chain
                self._json(verify_audit_chain(AUDIT_FILE))
            except Exception as e:
                self._json({"ok": False, "error": str(e)[:200]}, 500)
        elif path == "/api/plan":
            q = parse_qs(urlparse(self.path).query)
            pid = (q.get("project") or [""])[0].strip()
            data = plan_api(pid) if pid else None
            self._json(data if data else {"error": "缺少 project 参数或项目不存在"},
                       200 if data else 400)
        elif path == "/api/events":
            q = parse_qs(urlparse(self.path).query)
            try:
                since = int((q.get("since") or ["0"])[0])
            except ValueError:
                return self._json({"error": "since 必须是整数序号"}, 400)
            self._json(read_events(project=(q.get("project") or [""])[0].strip(),
                                   since=since,
                                   limit=(q.get("limit") or ["300"])[0]))
        elif path == "/api/ready-wave":
            # 推荐波（DAG 调度器，只读）：算出可派任务波次，不写任务状态。
            q = parse_qs(urlparse(self.path).query)
            pid = (q.get("project") or [""])[0].strip()
            data = ready_wave(pid) if pid else None
            self._json(data if data else {"error": "缺少 project 参数或项目不存在"},
                       200 if data else 400)
        elif path == "/api/launch-event":
            # 只读事件查询：launch 事件与普通事件同流，直接复用 read_events（向前兼容）。
            q = parse_qs(urlparse(self.path).query)
            try:
                since = int((q.get("since") or ["0"])[0])
            except ValueError:
                return self._json({"error": "since 必须是整数序号"}, 400)
            ev = read_events(project=(q.get("project") or [""])[0].strip(), since=since,
                             limit=(q.get("limit") or ["300"])[0])
            ev["events"] = [e for e in ev["events"]
                            if str(e.get("action", "")).startswith("launch:")]
            self._json(ev)
        elif path == "/api/launch-resolve":
            # 通用启动器 BOOT 解析（只读，绝不写状态）：project 必填。
            q = parse_qs(urlparse(self.path).query)
            pid = (q.get("project") or [""])[0].strip()
            if not pid:
                return self._json({"error": "缺少 project 参数"}, 400)
            ko = {}
            for key in ("mode", "tasks", "port", "model", "requirements", "seats", "notes"):
                if q.get(key):
                    ko[key] = q[key][0]
            self._json(launch_resolve(pid, kickoff=ko))
        elif path == "/api/stream":
            self._stream(parse_qs(urlparse(self.path).query))
        elif path == "/static" or path.startswith("/static/"):
            self._static(path)
        else:
            self._html(page("404", "/", "<h3>404</h3>"), 404)

    def do_POST(self):
        # R6：token 非空时，所有 POST 写接口先过 Bearer 鉴权；读接口仍可公开读取。
        if not self._require_token():
            return
        path = urlparse(self.path).path
        if path == "/api/launch-event":
            # 通用启动器事件总线（额外需求2/3）：JSON 或表单均可；只追加审计，不改任务状态。
            n = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(n).decode("utf-8", errors="replace") if n else ""
            payload = {}
            ctype = (self.headers.get("Content-Type") or "").lower()
            if "application/json" in ctype:
                try:
                    payload = json.loads(raw or "{}")
                except json.JSONDecodeError:
                    return self._json({"ok": False, "error": "JSON 解析失败"}, 400)
            else:
                payload = dict(parse_qs(raw, keep_blank_values=True).items())
            if not isinstance(payload, dict):
                return self._json({"ok": False, "error": "payload 必须是对象"}, 400)
            ok, msg = launch_event(payload)
            return self._json({"ok": ok, "message": msg}, 200 if ok else 400)
        f = self._form()
        if path == "/roles/add":
            ok, msg = add_role(f)
            self._html(page("结果", "/roles", f'<h2>{"✅" if ok else "❌"} 新增角色</h2><div class=card>{msg}</div><a class=btn href=/roles>返回角色页</a>'))
        elif path == "/roles/edit":
            ok, msg = edit_role(f)
            self._html(page("结果", "/roles", f'<h2>{"✅" if ok else "❌"} 编辑角色</h2><div class=card>{msg}</div><a class=btn href=/roles>返回</a>'))
        elif path.endswith("/delete") and path.startswith("/roles/"):
            ok, msg = delete_role(path.split("/")[2])
            self._html(page("结果", "/roles", f'<h2>{"✅" if ok else "❌"} 删除角色</h2><div class=card>{msg}</div><a class=btn href=/roles>返回</a>'))
        elif path == "/roles/common-config":
            res = [f"{x['id']}: {'ok' if apply_common_config(x['id']) else 'skip'}" for x in roster()["roles"]]
            audit("console", "common_config_applied", "", "; ".join(res))
            self._html(page("通用基座", "/roles", f'<h2>✅ 通用基座已应用到全员</h2><div class=card><pre>{chr(10).join(res)}</pre><p class=sub>裁剪列表：{COMMON_DISABLE}</p><p class=sub>改动在角色下次启动会话时生效（运行中的网关需重启）。</p></div><a class=btn href=/roles>返回</a>'))
        elif path == "/tasks/add":
            t = tasks()
            tid = f"T-{t['next_id']:03d}"
            ws = (f.get("workspace") or "").strip().rstrip("\\/")
            if not workspace_allowed(ws):
                return self._html(page("拒绝", "/tasks", f'<h2>❌ 工作目录不在白名单</h2><div class=card>{ALLOWED_ROOTS}</div><a class=btn href=/tasks>返回</a>'))
            if DENY_RE.search(f.get("verify_cmd", "")):
                return self._html(page("拒绝", "/tasks", '<h2>❌ 验收命令命中危险命令黑名单</h2><a class=btn href=/tasks>返回</a>'))
            role = next((x for x in roster()["roles"] if x["id"] == f.get("assignee")), None)
            if not role or role["ftype"] != "worker":
                return self._html(page("拒绝", "/tasks", '<h2>❌ 执行者必须是 流程权限=执行 的角色</h2><a class=btn href=/tasks>返回</a>'))
            rev = next((x for x in roster()["roles"] if x["id"] == f.get("reviewer")), None)
            if f.get("reviewer") and (not rev or rev["ftype"] != "reviewer"):
                return self._html(page("拒绝", "/tasks", '<h2>❌ 审查者必须是 流程权限=审查 的角色</h2><a class=btn href=/tasks>返回</a>'))
            pname = (f.get("new_project") or "").strip()
            pid = (f.get("project") or "").strip()
            if not pid and pname:
                pj = projects()
                pid = f"P-{pj['next_id']:03d}"
                pj["projects"].append({"pid": pid, "name": pname, "created_at": now(),
                                       "workspace": ws})
                pj["next_id"] += 1
                save_json(PROJECTS_FILE, pj)
                audit("console", "project_created", pid, pname,
                      url=task_event_url(project_id=pid))
            task = {"id": tid, "title": f.get("title", ""), "assignee": f.get("assignee"),
                    "reviewer": f.get("reviewer", ""), "workspace": ws, "project": pid,
                    "detail": f.get("detail", ""), "verify_cmd": f.get("verify_cmd", ""),
                    "state": "DRAFT", "created_at": now(), "history": []}
            t["tasks"].append(task)
            t["next_id"] += 1
            save_json(TASKS_FILE, t)
            audit("console", "task_created", tid, f'{task["title"]} project={pid or "—"}')
            self._redirect(f"/tasks/{tid}")
        elif path.startswith("/tasks/") and path.endswith("/plan"):
            tid = path.split("/")[2]
            actor = (f.get("actor") or "web-edit").strip()[:40]
            fields = {k: v for k, v in f.items() if k != "actor"}
            ok, msg = update_plan(tid, fields, actor=actor)
            self._html(page("计划更新", "/tasks",
                            f'<h2>{"✅ " + msg if ok else "❌ " + msg}</h2>'
                            f'<a class=btn href="/tasks/{tid}">返回任务详情</a> '
                            f'<a class=btn href="/projects">项目看板</a>'))
        elif path.startswith("/tasks/") and path.endswith("/dispatch"):
            tid = path.split("/")[2]
            task, _ = get_task(tid)
            if not task:
                return self._html(page("错误", "/tasks", "<h3>任务不存在</h3>"))
            rr = next((x for x in roster()["roles"] if x["id"] == task["assignee"]), None)
            if not rr or not port_listening(rr["port"]):
                audit("console", "dispatch_blocked_offline", tid, f"{task['assignee']} 网关离线")
                return self._html(page("拦截", "/tasks", f'<h2>⛔ 派工拦截：{task["assignee"]} 网关离线（端口 {rr["port"] if rr else "?"} 无监听）</h2><div class=card>请先到「角色」页启动该角色，绿灯后再派工——防假在线。</div><a class=btn href=/roles>去角色页</a> <a class=btn href=/tasks/{tid}>返回</a>'))
            blockers = dispatch_dependency_blockers(task)
            if blockers:
                detail = "; ".join(f"{bid}={bst}" for bid, bst in blockers)
                audit("console", "dispatch_blocked_dependency", tid, f"前置未完成：{detail}")
                return self._html(page("拦截", "/tasks", f'<h2>⛔ 派工拦截：前置任务未完成</h2><div class=card>需先完成：{detail}（仅 DONE/PARTIAL 可放行）。</div><a class=btn href=/projects>去项目看板</a> <a class=btn href=/tasks/{tid}>返回</a>'))
            if task["state"] != "ASSIGNED":  # 幂等重派：已在 ASSIGNED 态则直接续派
                ok, msg = transition(task, "ASSIGNED", "console", "网页派工")
                if not ok:
                    return self._html(page("拒绝", "/tasks", f'<h2>❌ {msg}</h2><a class=btn href=/tasks/{tid}>返回</a>'))
            task, _ = get_task(tid)
            if task["state"] == "ASSIGNED":
                transition(task, "DOING", "console", "派发中")
            dispatch_via_manager(task, "dispatch")
            audit("console", "dispatch", tid, f'派工 {task["assignee"]}：{task["title"][:80]}',
                  assignee=task.get("assignee", ""), reviewer=task.get("reviewer", ""),
                  url=task_event_url(task_id=tid))
            _pj = task.get("project") or ""
            self._html(page("派工", "/tasks", f'<h2>📤 已提交 Manager（后台执行）</h2><p class=sub>事件流：<a class=mono href="/api/events?project={_pj}">/api/events?project={_pj}</a> ｜ 任务：<a href="/tasks/{tid}">/tasks/{tid}</a></p><a class=btn href=/tasks/{tid}>刷新任务页看回执</a>'))
        elif path.startswith("/tasks/") and path.endswith("/verify"):
            tid = path.split("/")[2]
            task, _ = get_task(tid)
            if not task:
                return self._html(page("错误", "/tasks", "<h3>任务不存在</h3>"))
            if task["state"] not in ("SUBMITTED", "REVIEWING", "REWORK"):
                return self._html(page("拒绝", "/tasks", f'<h2>❌ 状态 {task["state"]} 不允许机器验收</h2><a class=btn href=/tasks/{tid}>返回</a>'))
            ok, out = machine_verify(task)
            task, _ = get_task(tid)
            task["verify_ok"] = ok
            t = tasks(); save_task(task, t)
            self._html(page("机器验收", "/tasks", f'<h2>{"✅ 机器验收通过" if ok else "❌ 机器验收失败"}</h2><pre>{out}</pre><p class=sub>PASS 记录以退出码为准。</p><a class=btn href=/tasks/{tid}>返回</a>'))
        elif path.startswith("/tasks/") and path.endswith("/review"):
            tid = path.split("/")[2]
            task, _ = get_task(tid)
            if not task:
                return self._html(page("错误", "/tasks", "<h3>任务不存在</h3>"))
            if not task.get("verify_ok"):
                return self._html(page("拒绝", "/tasks", '<h2>❌ 机器验收未通过，禁止送审</h2><a class=btn href=/tasks/{tid}>返回</a>'))
            if not task.get("reviewer"):
                return self._html(page("拒绝", "/tasks", '<h2>❌ 未指定审查者</h2><a class=btn href=/tasks/{tid}>返回</a>'))
            rv = next((x for x in roster()["roles"] if x["id"] == task.get("reviewer")), None)
            if not rv or not port_listening(rv["port"]):
                audit("console", "review_blocked_offline", tid, f"{task.get('reviewer')} 网关离线")
                return self._html(page("拦截", "/tasks", f'<h2>⛔ 送审拦截：{task.get("reviewer")} 网关离线</h2><div class=card>请先到「角色」页启动审查者。</div><a class=btn href=/roles>去角色页</a> <a class=btn href=/tasks/{tid}>返回</a>'))
            if task["state"] != "REVIEWING":
                ok, msg = transition(task, "REVIEWING", "console", "送审")
                if not ok:
                    return self._html(page("拒绝", "/tasks", f'<h2>❌ {msg}</h2><a class=btn href=/tasks/{tid}>返回</a>'))
                task, _ = get_task(tid)
                if not task:
                    return self._html(page("错误", "/tasks", "<h3>任务不存在</h3>"))
            dispatch_via_manager(task, "review")
            audit("console", "review", tid, f'送审 {task.get("reviewer")}：{task["title"][:80]}',
                  assignee=task.get("assignee", ""), reviewer=task.get("reviewer", ""),
                  url=task_event_url(task_id=tid))
            self._html(page("送审", "/tasks", f'<h2>⚖️ 已提交 Manager（后台执行）</h2><p class=sub>任务：<a href="/tasks/{tid}">/tasks/{tid}</a> ｜ 事件流：<a class=mono href="/api/events?since=0">/api/events</a></p><a class=btn href=/tasks/{tid}>刷新看判定</a>'))
        elif path.startswith("/tasks/") and path.endswith("/rework"):
            tid = path.split("/")[2]
            task, _ = get_task(tid)
            ok, msg = transition(task, "REWORK", "console", f.get("reason", "审查判定"))
            if ok:
                task, _ = get_task(tid)
                task["rework_count"] = task.get("rework_count", 0) + 1
                t = tasks(); save_task(task, t)
                transition(task, "ASSIGNED", "console", f"第{task['rework_count']}次返工")
                audit("console", "rework", tid, f"第{task['rework_count']}次返工：{f.get('reason', '审查判定')[:100]}",
                      assignee=task.get("assignee", ""), reviewer=task.get("reviewer", ""),
                      url=task_event_url(task_id=tid))
                self._html(page("返工", "/tasks", f'<h2>🔁 第 {task["rework_count"]} 次返工登记（上限3）</h2><p class=sub>任务：<a href="/tasks/{tid}">/tasks/{tid}</a> ｜ 事件流：<a class=mono href="/api/events?since=0">/api/events</a></p><a class=btn href=/tasks/{tid}>返回任务页重新派工</a>'))
            else:
                self._html(page("拒绝", "/tasks", f'<h2>❌ {msg}</h2><a class=btn href=/tasks/{tid}>返回</a>'))
        elif path.startswith("/tasks/") and path.endswith("/close"):
            tid = path.split("/")[2]
            task, _ = get_task(tid)
            if not task:
                return self._html(page("错误", "/tasks", "<h3>任务不存在</h3>"))
            # R3: DONE 硬门，未通过一律拒绝，不再允许直接 transition DONE
            import sys as _sys2
            if str(FLEET / "console") not in _sys2.path:
                _sys2.path.insert(0, str(FLEET / "console"))
            from domain import done_gate_reasons, resolve_completion_mode
            gate_errors = done_gate_reasons(task)
            if gate_errors:
                audit("console", "close_blocked_gate", tid, "; ".join(gate_errors)[:500],
                      assignee=task.get("assignee", ""), reviewer=task.get("reviewer", ""),
                      url=task_event_url(task_id=tid))
                return self._html(page("拒绝", "/tasks", f'<h2>❌ 收口被门禁拒绝</h2><div class=card>{"<br>".join(gate_errors)}</div><p class=sub>需先通过机器验收、reviewer PASS、CLI transcript 与证据门。</p><a class=btn href=/tasks/{tid}>返回</a>'))
            task["completion_mode"] = resolve_completion_mode(task)
            t = tasks(); save_task(task, t)
            ok, msg = transition(task, "DONE", "console", f.get("note", "门禁通过收口"))
            report_path = completion_report(task.get("project"), task) if ok and task.get("project") else None
            if ok:
                audit("console", "close", tid, f"人工收口 DONE：{f.get('note', '')[:100]}",
                      assignee=task.get("assignee", ""), reviewer=task.get("reviewer", ""),
                      url=task_event_url(task_id=tid))
            report_link = (f'<p>完成度报告：<a href="/reports/{report_path.name}">{report_path.name}</a></p>'
                           if report_path else '')
            self._html(page("收口", "/tasks", f'<h2>{"✅ DONE" if ok else "❌ " + msg}</h2>{report_link}<p class=sub>任务：<a href="/tasks/{tid}">/tasks/{tid}</a> ｜ 项目看板：<a href="/projects">/projects</a> ｜ 事件流：<a class=mono href="/api/events?since=0">/api/events</a></p><a class=btn href=/tasks/{tid}>返回</a>'))
        elif path == "/fleet/start":
            results = []
            ok, out = run(f'"{HERMES_BIN}" gateway start', 60)
            results.append(f"manager: {'ok' if ok else out[-100:]}")
            for x in roster()["roles"]:
                ok, msg = start_role(x["id"])
                results.append(f"{x['id']}: {msg}")
            self._html(page("舰队启动", "/", "<h2>舰队启动</h2><pre>" + "\n".join(results) + "</pre><a class=btn href=/>返回</a>"))
        else:
            self._html(page("404", "/", "<h3>404</h3>"), 404)


if __name__ == "__main__":
    audit("console", "console_started", "", f"pid={os.getpid()}")
    print(f"AideanAgentFleet 控制台 v3 ({CONSOLE_VERSION}): http://127.0.0.1:5000 (仅本机)")
    print("新路由：POST /api/launch-event · GET /api/launch-resolve · GET /api/launch-event?project=&since=")
    ThreadingHTTPServer(("127.0.0.1", 5000), Handler).serve_forever()

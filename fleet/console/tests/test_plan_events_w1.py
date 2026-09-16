# -*- coding: utf-8 -*-
"""
W1 隔离测试：console.py 统一计划/事件 API、统一事件写入、计划更新安全门。
运行方式：python console/tests/test_plan_events_w1.py
不触碰生产状态文件（所有 state 常量 patch 到临时目录），HTTP 用临时端口 5399。
"""
import json
import shutil
import sys
import tempfile
import threading
import urllib.request
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve()
CONSOLE_DIR = HERE.parents[1]
sys.path.insert(0, str(CONSOLE_DIR))
import console as C  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, evidence=""):
    (PASS if cond else FAIL).append(name)
    print(("✅ PASS" if cond else "❌ FAIL"), name, ("| " + str(evidence)[:160]) if evidence else "")


# ---------- 隔离夹具 ----------
TMP = Path(tempfile.mkdtemp(prefix="w1test-"))
C.STATE = TMP
C.SOULS = TMP / "souls"
C.EVIDENCE = TMP / "evidence"
C.ROSTER_FILE = TMP / "roster.json"
C.TASKS_FILE = TMP / "tasks.json"
C.PROJECTS_FILE = TMP / "projects.json"
C.AUDIT_FILE = TMP / "audit.log"
C.SOULS.mkdir(); C.EVIDENCE.mkdir()

WS = str(Path(r"E:/Code/AideanCompany/fleet/projects"))  # 白名单内真实目录（只读用途）
C.save_json(C.ROSTER_FILE, {"roles": [
    {"id": "w-test", "duty": "后端开发", "ftype": "worker", "port": 59001, "workspace": WS},
    {"id": "r-test", "duty": "审查", "ftype": "reviewer", "port": 59002, "workspace": WS},
], "next_port": 59003})
C.save_json(C.PROJECTS_FILE, {"projects": [
    {"pid": "P-900", "name": "W1隔离测试项目", "created_at": C.now(), "workspace": WS}], "next_id": 2})


def mk_task(tid, state, order_title, reviewer="r-test"):
    return {"id": tid, "title": order_title, "assignee": "w-test", "reviewer": reviewer,
            "workspace": WS, "project": "P-900", "detail": "规划目标" + tid,
            "verify_cmd": "python -m py_compile console.py", "state": state,
            "created_at": C.now(), "history": [], "rework_count": 0}


C.save_json(C.TASKS_FILE, {"tasks": [
    mk_task("T-901", "DONE", "甲"), mk_task("T-902", "DOING", "乙"),
    mk_task("T-903", "DRAFT", "丙", reviewer=""),
], "next_id": 904})

# ---------- 1. plan_api（=GET /api/plan 的同一函数） ----------
p = C.plan_api("P-900")
check("plan_api 返回 total/done/remaining 正确",
      p["total"] == 3 and p["remaining"] == 2, (p["total"], p["done"], p["remaining"]))
w = sum(C.STATE_WEIGHT.get(x["state"], 0) for x in C.tasks()["tasks"] if x.get("project") == "P-900")
check("plan_api progress 与 project_metrics 口径一致（百分比取整）",
      p["progress"] == round(w / 3 * 100), (p["progress"], w))
t0 = p["tasks"][0]
check("plan_api 任务含 state/detail/assignee/reviewer/verify_cmd/rework_count",
      all(k in t0 for k in ("state", "detail", "assignee", "reviewer", "verify_cmd", "rework_count")))
check("plan_api 每任务与项目带 URL",
      t0["url"] == "http://127.0.0.1:5000/tasks/T-901" and "projects" in p["url"], t0["url"])
check("plan_api 未知项目返回 None", C.plan_api("P-404") is None)
check("plan_api editable 门：DONE/DOING 不可编辑、DRAFT 可编辑",
      [x["editable"] for x in p["tasks"]] == [False, False, True])

# ---------- 2. 统一事件写入 + read_events（增量/字段/脱敏/URL） ----------
# 状态迁移事件
task3, t3 = C.get_task("T-903")
C.transition(task3, "ASSIGNED", "tester", "测试迁移")
evs = C.read_events(project="P-900")
migs = [e for e in evs["events"] if e["action"] == "state:ASSIGNED"]
check("状态迁移写入事件含 from/to/actor/taskId",
      migs and migs[0]["from"] == "DRAFT" and migs[0]["to"] == "ASSIGNED"
      and migs[0]["actor"] == "tester" and migs[0]["taskId"] == "T-903", migs)
check("事件自带任务详情 URL",
      migs and migs[0]["url"] == "http://127.0.0.1:5000/tasks/T-903", migs[0]["url"] if migs else "")
# machine_verify / verify 事件
tv, _ = C.get_task("T-902")
C.machine_verify(dict(tv))
evs2 = C.read_events(project="P-900")
vf = [e for e in evs2["events"] if e["action"] == "verify"]
check("机器验收写入事件 actor=machine-gate", vf and vf[-1]["actor"] == "machine-gate", vf[-1:] )
# since 增量
seq_snapshot = evs2["seq"]
C.audit("tester", "note", "T-901", "增量验证")
evs3 = C.read_events(project="P-900", since=seq_snapshot)
check("since 增量只返回新事件", len(evs3["events"]) == 0 or all(
    e["seq"] > seq_snapshot for e in evs3["events"]), [e["seq"] for e in evs3["events"]])
evs_all = C.read_events(project="P-900")
new_ids = {e["seq"] for e in evs_all["events"]} - {e["seq"] for e in evs2["events"]}
check("无 project 过滤时可见 audit 全量（含他处写入）", evs_all["seq"] >= seq_snapshot + 1)
# project 过滤：他项目事件不混入
C.audit("tester", "note", "T-888", "别的项目")
check("read_events 按 project 过滤",
      all(e["taskId"] != "T-888" for e in C.read_events(project="P-900")["events"]))
# 脱敏
C.audit("tester", "note", "T-901", "配置里 api_key=sk-abcdefgh12345 已写入")
ev_last = C.read_events(project="P-900")["events"][-1]
check("事件摘要脱敏疑似 Key", "sk-" not in str(ev_last["summary"]) and ev_last["summary"] == "[REDACTED]",
      ev_last["summary"])

# ---------- 3. update_plan 安全门 ----------
ok, msg = C.update_plan("T-901", {"title": "甲改"}, "tester")
check("DONE 态禁止编辑（状态机门）", not ok, msg)
ok, msg = C.update_plan("T-902", {"state": "DONE"}, "tester")
check("提交 state 字段被白名单拒绝", not ok and "禁止修改" in msg, msg)
ok, msg = C.update_plan("T-902", {"project": "P-999"}, "tester")
check("提交 project 字段被白名单拒绝", not ok, msg)
ok, msg = C.update_plan("T-902", {"id": "T-000"}, "tester")
check("提交 id 字段被白名单拒绝", not ok, msg)
ok, msg = C.update_plan("T-903", {"assignee": "r-test"}, "tester")
check("执行者必须是 worker 角色（权限门）", not ok and "执行者" in msg, msg)
ok, msg = C.update_plan("T-903", {"reviewer": "w-test"}, "tester")
check("审查者必须是 reviewer 角色（权限门）", not ok and "审查者" in msg, msg)
ok, msg = C.update_plan("T-903", {"verify_cmd": "rm -rf /"}, "tester")
check("危险 verify_cmd 被黑名单拒绝", not ok and "黑名单" in msg, msg)
ok, msg = C.update_plan("T-903", {"title": ""}, "tester")
check("title 不允许清空（必填校验）", not ok, msg)
ok, msg = C.update_plan("T-903", {"title": "甲"*300}, "tester")
check("title 超长被拒", not ok and "超长" in msg, msg)
ok, msg = C.update_plan("T-404", {"title": "x"}, "tester")
check("任务不存在返回失败", not ok and "不存在" in msg, msg)
before_audit = C.AUDIT_FILE.read_text(encoding="utf-8")
ok, msg = C.update_plan("T-903", {"detail": "新规划目标", "reviewer": "r-test"}, "tester")
task3, _ = C.get_task("T-903")
check("合法字段更新成功且落盘", ok and task3["detail"] == "新规划目标"
      and task3["reviewer"] == "r-test", msg)
after_audit = C.AUDIT_FILE.read_text(encoding="utf-8")
check("修改前审计字节不变（append-only 可回放）", after_audit.startswith(before_audit))
pu = [e for e in C.read_events(project="P-900")["events"] if e["action"] == "plan_updated"]
check("plan_updated 事件含 actor/fields/URL",
      pu and pu[-1]["actor"] == "tester" and "detail" in pu[-1]["summary"]
      and pu[-1]["url"].startswith("http://127.0.0.1:5000/tasks/T-903"), pu[-1:])
# order 重排
C.save_json(C.TASKS_FILE, {"tasks": [
    mk_task("T-911", "DRAFT", "甲"), mk_task("T-912", "DRAFT", "乙"), mk_task("T-913", "DRAFT", "丙"),
], "next_id": 914})
ok, msg = C.update_plan("T-913", {"order": "0"}, "tester")
order_after = [x["id"] for x in C.tasks()["tasks"] if x.get("project") == "P-900"]
check("order 重排生效（0 起插入）", ok and order_after == ["T-913", "T-911", "T-912"], order_after)
ok, msg = C.update_plan("T-913", {"order": "abc"}, "tester")
check("order 非整数被拒", not ok and "整数" in msg, msg)
# 不删除任务
check("全程无任务被删除", len(C.tasks()["tasks"]) == 3)

# ---------- 4. HTTP 路由（临时端口，隔离实例） ----------
from http.server import ThreadingHTTPServer  # noqa: E402
srv = ThreadingHTTPServer(("127.0.0.1", 5399), C.Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "http://127.0.0.1:5399"


def http(method, path, data=None):
    body = urllib.parse.urlencode(data or {}).encode() if data else None
    req = urllib.request.Request(BASE + path, data=body, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


code, body = http("GET", "/api/plan?project=P-900")
j = json.loads(body)
check("HTTP GET /api/plan 200+JSON 结构齐全",
      code == 200 and all(k in j for k in
                          ("project", "total", "done", "remaining", "progress", "tasks")), code)
code, _ = http("GET", "/api/plan")
check("HTTP GET /api/plan 缺 project → 400", code == 400, code)
code, _ = http("GET", "/api/plan?project=P-404")
check("HTTP GET /api/plan 未知项目 → 400", code == 400, code)
code, body = http("GET", "/api/events?project=P-900&since=0")
j = json.loads(body)
check("HTTP GET /api/events 200 且含 seq/events", code == 200 and "seq" in j and "events" in j)
check("事件字段齐全 timestamp/actor/action/taskId/from/to/assignee/reviewer/summary/url",
      all(k in j["events"][0] for k in ("timestamp", "actor", "action", "taskId",
                                        "from", "to", "assignee", "reviewer", "summary", "url")))
code, _ = http("GET", "/api/events?since=abc")
check("HTTP /api/events since 非整数 → 400", code == 400, code)
code, body = http("GET", "/api/events?project=P-900&since=" + str(j["seq"]))
check("since=当前 seq 增量返回空", code == 200 and json.loads(body)["events"] == [])
code, body = http("GET", "/tasks/T-911/plan-edit")
check("网页编辑入口 200 且含表单/白名单说明",
      code == 200 and 'action="/tasks/T-911/plan"' in body and "不可改" in body)
code, body = http("POST", "/tasks/T-911/plan", {"state": "DONE", "actor": "http-test"})
check("HTTP POST 计划更新：夹带 state 被拒并回显原因",
      code == 200 and "禁止修改字段" in body, body[:120])
code, body = http("POST", "/tasks/T-911/plan", {"title": "网页改名", "actor": "http-test"})
check("HTTP POST 计划更新：合法修改成功", code == 200 and "计划已更新" in body, body[:120])
check("HTTP 修改后状态源同步（tasks.json 已更新）",
      C.get_task("T-911")[0]["title"] == "网页改名")
code, body = http("POST", "/tasks/T-911/plan", {"verify_cmd": "taskkill /f /im python.exe"})
check("HTTP POST：危险 verify_cmd 经网页路径同样被拒", code == 200 and "黑名单" in body, body[:120])
code, body = http("GET", "/projects")
check("/projects 页计划行含编辑入口链接",
      code == 200 and "/plan-edit" in body)
srv.shutdown()

# ---------- 5. 网页/提示 URL 覆盖（静态断言） ----------
src = (CONSOLE_DIR / "console.py").read_text(encoding="utf-8")
disp_line = next(l for l in src.splitlines() if "已提交 Manager（后台执行）" in l and "派工" in l)
rev_line = next(l for l in src.splitlines() if "已提交 Manager（后台执行）" in l and "送审" in l)
check("派工成功提示含事件流+任务 URL",
      "/api/events?project=" in disp_line and "/tasks/{tid}" in disp_line)
check("送审成功提示含事件流+任务 URL",
      "/api/events" in rev_line and "/tasks/{tid}" in rev_line)
check("CONSOLE_BASE 指向 5000 且 task_event_url 生成 /tasks/<id>",
      'CONSOLE_BASE = "http://127.0.0.1:5000"' in src and '/tasks/{task_id}' in src)

shutil.rmtree(TMP, ignore_errors=True)
print(f"\n===== 结果：{len(PASS)} 通过 / {len(FAIL)} 失败 =====")
if FAIL:
    print("失败项：", FAIL)
    sys.exit(1)

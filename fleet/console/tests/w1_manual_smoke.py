# -*- coding: utf-8 -*-
"""手工冒烟：隔离临时数据 + 临时端口，打印真实响应（供报告原样引用），测完即清理。"""
import json, sys, tempfile, threading, shutil, urllib.request, urllib.error
from pathlib import Path
from http.server import ThreadingHTTPServer
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import console

tmp = Path(tempfile.mkdtemp(prefix="fleet-w1-smoke-")); st = tmp / "state"; st.mkdir()
console.FLEET, console.STATE = tmp, st
console.SOULS, console.EVIDENCE = st/"souls", st/"evidence"
console.LOGS = tmp/"logs"
console.ROSTER_FILE, console.TASKS_FILE = st/"roster.json", st/"tasks.json"
console.PROJECTS_FILE, console.AUDIT_FILE = st/"projects.json", st/"audit.log"
for d in (console.SOULS, console.EVIDENCE, console.LOGS): d.mkdir()
console.ALLOWED_ROOTS = [str(tmp)]
console.save_json(console.ROSTER_FILE, {"roles":[{"id":"be-2x","ftype":"worker","duty":"后端","port":9991,"model":{"model_id":"m","base_url":"http://x"}},{"id":"rv-1x","ftype":"reviewer","duty":"审","port":9992,"model":{"model_id":"m","base_url":"http://x"}}],"next_port":9993})
console.save_json(console.PROJECTS_FILE, {"projects":[{"pid":"P-001","name":"冒烟项目","workspace":str(tmp),"created_at":console.now()}],"next_id":2})
console.save_json(console.TASKS_FILE, {"next_id":2,"tasks":[{"id":"T-001","title":"冒烟任务","assignee":"be-2x","reviewer":"rv-1x","workspace":str(tmp),"project":"P-001","detail":"目标","verify_cmd":"grep:a.txt:foo","state":"DRAFT","created_at":console.now(),"history":[]}]})
t0, tl = console.get_task("T-001"); console.transition(t0,"ASSIGNED","console","派工"); console.audit("console","dispatch","T-001","派工 be-2x",assignee="be-2x",reviewer="rv-1x")
srv = ThreadingHTTPServer(("127.0.0.1", 0), console.Handler); port = srv.server_address[1]
console.CONSOLE_BASE = f"http://127.0.0.1:{port}"
threading.Thread(target=srv.serve_forever, daemon=True).start()

def get(p):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{p}", timeout=10) as r:
        return r.status, r.read().decode("utf-8")
def code_err(p):
    try:
        return get(p)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8")

for p in ["/api/plan?project=P-001", "/api/events?project=P-001&since=0", "/api/plan?project=NOPE", "/api/events?since=abc"]:
    c, b = code_err(p)
    print(f"GET {p}\n  -> HTTP {c}\n  {b[:400]}\n")
import urllib.parse
d = urllib.parse.urlencode({"title":"冒烟任务改","detail":"新目标","verify_cmd":"rm -rf /","assignee":"be-2x","reviewer":"","actor":"web-edit"}).encode()
req = urllib.request.Request(f"http://127.0.0.1:{port}/tasks/T-001/plan", data=d, method="POST")
with urllib.request.urlopen(req, timeout=10) as r:
    body = r.read().decode("utf-8")
print("POST /tasks/T-001/plan (verify_cmd=rm -rf / 危险命令)\n  -> HTTP", r.status, "| 页面含拒绝:", "危险命令黑名单" in body)
srv.shutdown(); srv.server_close(); shutil.rmtree(tmp, ignore_errors=True)
print("cleanup done")

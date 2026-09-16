# -*- coding: utf-8 -*-
"""W1 隔离测试：统一计划/事件 API、统一事件写入、计划更新安全接口。
不触碰生产 state 目录：全部数据落在 tempfile，测试服务用临时端口，测完清理。
运行：python fleet/console/tests/test_plan_api_w1.py
"""
import json
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import console  # noqa: E402


class PlanApiW1Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="fleet-w1-test-"))
        st = cls.tmp / "state"
        st.mkdir()
        # 隔离：把模块级路径全部重定向到临时目录
        console.FLEET = cls.tmp
        console.STATE = st
        console.SOULS = st / "souls"
        console.EVIDENCE = st / "evidence"
        console.LOGS = cls.tmp / "logs"
        console.ROSTER_FILE = st / "roster.json"
        console.TASKS_FILE = st / "tasks.json"
        console.PROJECTS_FILE = st / "projects.json"
        console.AUDIT_FILE = st / "audit.log"
        console.SOULS.mkdir(); console.EVIDENCE.mkdir(); console.LOGS.mkdir()
        console.ALLOWED_ROOTS = [str(cls.tmp)]

        console.save_json(console.ROSTER_FILE, {"roles": [
            {"id": "be-2x", "ftype": "worker", "duty": "后端", "port": 9991,
             "model": {"model_id": "m1", "base_url": "http://x"}},
            {"id": "rv-1x", "ftype": "reviewer", "duty": "审查", "port": 9992,
             "model": {"model_id": "m2", "base_url": "http://x"}},
        ], "next_port": 9993})
        console.save_json(console.PROJECTS_FILE, {"projects": [
            {"pid": "P-001", "name": "测试项目", "workspace": str(cls.tmp), "created_at": console.now()}
        ], "next_id": 2})
        tasks = {"next_id": 4, "tasks": [
            {"id": "T-001", "title": "已完成任务", "assignee": "be-2x", "reviewer": "rv-1x",
             "workspace": str(cls.tmp), "project": "P-001", "detail": "d1",
             "verify_cmd": "grep:a.txt:foo", "state": "DONE", "created_at": console.now(),
             "history": [], "rework_count": 1},
            {"id": "T-002", "title": "草案任务", "assignee": "be-2x", "reviewer": "",
             "workspace": str(cls.tmp), "project": "P-001", "detail": "d2",
             "verify_cmd": "grep:b.txt:bar", "state": "DRAFT", "created_at": console.now(),
             "history": []},
            {"id": "T-003", "title": "执行中任务", "assignee": "be-2x", "reviewer": "rv-1x",
             "workspace": str(cls.tmp), "project": "P-001", "detail": "d3",
             "verify_cmd": "grep:c.txt:baz", "state": "DOING", "created_at": console.now(),
             "history": []},
        ]}
        console.save_json(console.TASKS_FILE, tasks)

        # 统一事件写入验证：状态迁移应写 from/to/url
        t0, tl = console.get_task("T-003")
        ok, _ = console.transition(t0, "SUBMITTED", "manager", "测试迁移")
        cls.transition_ok = ok
        console.audit("console", "dispatch", "T-001", "派工 be-2x", assignee="be-2x")
        console.audit("console", "secret_probe", "T-001", "含敏感 detail: api_key=sk-1234567890")

        console.CONSOLE_BASE = None  # 先置空，下面按测试端口回填
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), console.Handler)
        cls.port = cls.server.server_address[1]
        console.CONSOLE_BASE = f"http://127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # ---- helpers ----
    def get(self, path):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=10) as r:
                return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

    def post(self, path, fields):
        data = urllib.parse.urlencode(fields).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

    def jget(self, path):
        code, body = self.get(path)
        return code, json.loads(body)

    # ---- /api/plan ----
    def test_plan_counts_and_fields(self):
        code, d = self.jget("/api/plan?project=P-001")
        self.assertEqual(code, 200)
        self.assertEqual(d["project"], "P-001")
        self.assertEqual(d["total"], 3)
        self.assertEqual(d["done"], 1)
        self.assertEqual(d["remaining"], 2)
        self.assertIsInstance(d["progress"], int)
        self.assertEqual([x["id"] for x in d["tasks"]], ["T-001", "T-002", "T-003"])
        for x in d["tasks"]:
            for k in ("state", "detail", "assignee", "reviewer", "verify_cmd", "rework_count", "url"):
                self.assertIn(k, x)
            self.assertTrue(x["url"].endswith(f"/tasks/{x['id']}"))
            self.assertEqual(x["editable"], x["state"] in console.PLAN_EDITABLE_STATES)

    def test_plan_bad_project_400(self):
        code, d = self.jget("/api/plan?project=NOPE")
        self.assertEqual(code, 400)
        self.assertIn("error", d)
        code2, d2 = self.jget("/api/plan")
        self.assertEqual(code2, 400)

    # ---- /api/events ----
    def test_events_shape_and_incremental(self):
        code, d = self.jget("/api/events?project=P-001&since=0")
        self.assertEqual(code, 200)
        self.assertGreater(d["seq"], 0)
        acts = {e["action"] for e in d["events"]}
        self.assertIn("state:SUBMITTED", acts)
        ev = next(e for e in d["events"] if e["action"] == "state:SUBMITTED")
        self.assertEqual(ev["taskId"], "T-003")
        self.assertEqual((ev["from"], ev["to"]), ("DOING", "SUBMITTED"))
        self.assertEqual(ev["actor"], "manager")
        self.assertTrue(ev["url"].endswith("/tasks/T-003"))
        # since 增量：取尾序号再拉一次应为空
        since = d["seq"]
        _, d2 = self.jget(f"/api/events?project=P-001&since={since}")
        self.assertEqual(d2["events"], [])
        _, all1 = self.jget("/api/events?since=0")
        self.assertEqual(len(all1["events"]), len(d["events"]))

    def test_events_redacts_secrets(self):
        _, d = self.jget("/api/events?since=0")
        probe = [e for e in d["events"] if e["action"] == "secret_probe"]
        self.assertTrue(probe)
        self.assertNotIn("sk-1234567890", json.dumps(probe, ensure_ascii=False))
        self.assertEqual(probe[0]["summary"], "[REDACTED]")

    def test_events_bad_since_400(self):
        code, d = self.jget("/api/events?since=abc")
        self.assertEqual(code, 400)
        self.assertIn("error", d)

    # ---- 计划更新接口 ----
    def _plan_form(self, **over):
        f = {"title": "草案任务", "detail": "d2", "verify_cmd": "grep:b.txt:bar",
             "assignee": "be-2x", "reviewer": "", "actor": "web-edit"}
        f.update(over)
        return f

    def test_update_allowed_fields(self):
        code, _ = self.post("/tasks/T-002/plan", self._plan_form(title="草案任务V2", detail="新目标"))
        self.assertEqual(code, 200)
        task, _ = console.get_task("T-002")
        self.assertEqual(task["title"], "草案任务V2")
        self.assertEqual(task["detail"], "新目标")
        last = console.AUDIT_FILE.read_text(encoding="utf-8").splitlines()[-1]
        rec = json.loads(last)
        self.assertEqual((rec["action"], rec["task"]), ("plan_updated", "T-002"))
        self.assertIn("title", rec["detail"])
        self.assertTrue(rec["url"].endswith("/tasks/T-002"))

    def test_update_forbidden_fields_ignored(self):
        code, body = self.post("/tasks/T-002/plan", self._plan_form(
            title="禁改测试", state="DONE", project="P-999", id="T-999"))
        self.assertEqual(code, 200)
        self.assertIn("禁止修改字段", body)
        task, _ = console.get_task("T-002")
        self.assertEqual(task["state"], "DRAFT")       # 未动
        self.assertEqual(task["project"], "P-001")     # 未动
        self.assertEqual(task["id"], "T-002")          # 未动
        self.assertNotEqual(task["title"], "禁改测试")  # 混合提交含禁改字段→整体拒绝

    def test_update_dangerous_verify_cmd_rejected(self):
        code, body = self.post("/tasks/T-002/plan", self._plan_form(verify_cmd="rmdir /s C:\\x"))
        self.assertEqual(code, 200)
        self.assertIn("危险命令黑名单", body)
        task, _ = console.get_task("T-002")
        self.assertEqual(task["verify_cmd"], "grep:b.txt:bar")

    def test_update_role_permission_enforced(self):
        code, body = self.post("/tasks/T-002/plan", self._plan_form(assignee="rv-1x"))
        self.assertIn("执行者必须是流程权限=执行", body)
        code, body = self.post("/tasks/T-002/plan", self._plan_form(reviewer="be-2x"))
        self.assertIn("审查者必须是流程权限=审查", body)

    def test_update_state_gate_enforced(self):
        code, body = self.post("/tasks/T-001/plan", self._plan_form(title="想改DONE"))
        self.assertIn("禁止编辑", body)
        task, _ = console.get_task("T-001")
        self.assertEqual(task["title"], "已完成任务")

    def test_update_order_reorders_within_project(self):
        code, _ = self.post("/tasks/T-002/plan", self._plan_form(order="0"))
        self.assertEqual(code, 200)
        _, d = self.jget("/api/plan?project=P-001")
        self.assertEqual(d["tasks"][0]["id"], "T-002")
        # 越界序号被钳制，任务不丢失
        self.post("/tasks/T-002/plan", self._plan_form(order="99"))
        _, d = self.jget("/api/plan?project=P-001")
        self.assertEqual(sorted(x["id"] for x in d["tasks"]), ["T-001", "T-002", "T-003"])
        self.assertEqual(d["tasks"][-1]["id"], "T-002")

    def test_update_empty_and_unknown_via_api_layer(self):
        ok, msg = console.update_plan("T-002", {"state": "DONE"})
        self.assertFalse(ok); self.assertIn("禁止修改字段", msg)
        ok, msg = console.update_plan("T-002", {})
        self.assertFalse(ok)
        ok, msg = console.update_plan("T-404", {"title": "x"})
        self.assertFalse(ok); self.assertIn("任务不存在", msg)

    # ---- 统一事件 URL（任务详情/项目） ----
    def test_event_url_construction(self):
        self.assertTrue(console.task_event_url(task_id="T-002").endswith("/tasks/T-002"))
        u = console.task_event_url(project_id="P-001")
        self.assertIn("/projects", u); self.assertIn("P-001", u)

    # ---- 网页编辑入口存在性 ----
    def test_edit_entry_pages(self):
        code, body = self.get("/tasks/T-002/plan-edit")
        self.assertEqual(code, 200)
        self.assertIn("编辑计划", body)
        self.assertIn('/tasks/T-002/plan"', body)
        code, body = self.get("/tasks/T-001/plan-edit")   # DONE 不可编辑
        self.assertIn("禁止编辑", body)
        code, body = self.get("/projects")
        self.assertIn("plan-edit", body)                   # 计划大纲上有编辑入口


if __name__ == "__main__":
    unittest.main(verbosity=2)

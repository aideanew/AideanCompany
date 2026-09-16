# -*- coding: utf-8 -*-
"""G3 集成测试：/projects 实时计划页接线 + /static + /api/stream + 状态机门联动。
隔离：模块级 state 全部重定向到 tempfile（不触碰生产数据），HTTP 用临时端口。
运行：python fleet/console/tests/test_plan_integration_w3.py
"""
import json
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import console  # noqa: E402


class PlanIntegrationW3Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="fleet-w3-"))
        st = cls.tmp / "state"
        st.mkdir()
        cls._old = {}
        for name in ("FLEET", "STATE", "SOULS", "EVIDENCE", "LOGS", "ROSTER_FILE",
                     "TASKS_FILE", "PROJECTS_FILE", "AUDIT_FILE", "STATIC_DIR", "CONSOLE_BASE"):
            cls._old[name] = getattr(console, name)
        console.FLEET = cls.tmp
        console.STATE = st
        console.SOULS = st / "souls"; console.SOULS.mkdir()
        console.EVIDENCE = st / "evidence"; console.EVIDENCE.mkdir()
        console.LOGS = cls.tmp / "logs"; console.LOGS.mkdir()
        console.ROSTER_FILE = st / "roster.json"
        console.TASKS_FILE = st / "tasks.json"
        console.PROJECTS_FILE = st / "projects.json"
        console.AUDIT_FILE = st / "audit.log"
        console.STATIC_DIR = cls._old["STATIC_DIR"]  # 静态资源指向真实目录（被测对象）

        console.save_json(console.ROSTER_FILE, {"roles": [
            {"id": "w3-worker", "duty": "后端", "ftype": "worker", "port": 59301,
             "card": "W3W", "model": {"model_id": "m", "base_url": "http://x"}},
            {"id": "w3-reviewer", "duty": "审查", "ftype": "reviewer", "port": 59302,
             "card": "W3R", "model": {"model_id": "m", "base_url": "http://x"}},
        ], "next_port": 59303})
        console.save_json(console.PROJECTS_FILE, {"projects": [
            {"pid": "P-W3", "name": "W3集成项目", "workspace": str(cls.tmp),
             "created_at": console.now()}], "next_id": 2})
        mk = lambda tid, state, title: {"id": tid, "title": title, "assignee": "w3-worker",
                                        "reviewer": "w3-reviewer", "workspace": str(cls.tmp),
                                        "project": "P-W3", "detail": "目标" + tid,
                                        "verify_cmd": "python -m py_compile console.py",
                                        "state": state, "created_at": console.now(),
                                        "history": [], "rework_count": 0}
        console.save_json(console.TASKS_FILE, {"tasks": [
            mk("T-W3A", "DRAFT", "可编辑任务"), mk("T-W3B", "DONE", "已完成任务")],
            "next_id": 3})
        console.audit("console", "task_created", "T-W3A", "种子")
        console.audit("console", "task_created", "T-W3B", "种子")

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), console.Handler)
        cls.port = cls.server.server_address[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        console.CONSOLE_BASE = cls.base
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        for name, v in cls._old.items():
            setattr(console, name, v)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def get(self, path, timeout=10):
        try:
            with urllib.request.urlopen(self.base + path, timeout=timeout) as r:
                return r.status, dict(r.headers), r.read()
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), e.read()

    # ---- 需求1：从上到下进度条大纲 + 展开详情 + 整体百分比 ----
    def test_projects_topdown_progress_outline(self):
        code, _, body = self.get("/projects")
        self.assertEqual(code, 200)
        html = body.decode("utf-8")
        self.assertIn('class="plan-list"', html, "应有从上到下的计划容器")
        self.assertIn('class="plan card" data-pid="P-W3"', html, "计划区块应带 data-pid")
        self.assertIn("整体完成百分比", html, "应展示整体完成百分比")
        self.assertIn("已完成 1 / 共 2 项，剩余 1 项", html, "应展示 一共/已做/未做")
        self.assertIn('<details class="plan-task"', html, "大纲行应可展开（details）")
        self.assertIn("<summary>", html, "大纲行应有 summary 头")
        self.assertIn("规划目标", html, "展开应含流程说明（目标）")
        self.assertIn("验收标准", html, "展开应含验收标准")
        self.assertIn("执行者", html, "展开应含执行者")

    # ---- 需求2：计划可随时修改 + 状态机门关联（编辑入口条件渲染）----
    def test_edit_entry_state_gated(self):
        code, _, body = self.get("/projects")
        html = body.decode("utf-8")
        anchor_a = 'href="/tasks/T-W3A"'
        anchor_b = 'href="/tasks/T-W3B"'
        self.assertIn(anchor_a, html)
        self.assertIn(anchor_b, html)
        draft_row = html.split(anchor_a, 1)[1].split("</details>", 1)[0]
        done_row = html.split(anchor_b, 1)[1].split("</details>", 1)[0]
        self.assertIn("plan-edit", draft_row, "DRAFT 行应有编辑计划入口（随时可改）")
        self.assertNotIn("plan-edit", done_row, "DONE 行不得有编辑入口（状态机门）")

    # ---- 需求3：前后端连通 —— 页面必须引入同步组件并启动 ----
    def test_projects_wires_sync_client(self):
        code, _, body = self.get("/projects")
        html = body.decode("utf-8")
        self.assertIn("/static/js/plan-sync-client.js", html, "应引入前端同步组件")
        self.assertIn("FleetPlanSync.start()", html, "应自动启动同步")

    # ---- /static 路由（组件可达性）----
    def test_static_js_200_mime_and_size(self):
        code, headers, body = self.get("/static/js/plan-sync-client.js")
        self.assertEqual(code, 200)
        self.assertIn("javascript", headers.get("Content-Type", ""), "JS MIME 必须正确")
        self.assertGreater(len(body), 5000, "组件不应为空壳")
        self.assertIn(b"FleetPlanSync", body, "应返回同步组件本体")

    def test_static_traversal_and_missing_404(self):
        code, _, _ = self.get("/static/../state/tasks.json")
        self.assertEqual(code, 404, "路径穿越必须 404")
        code2, _, _ = self.get("/static/js/nope-not-exist.js")
        self.assertEqual(code2, 404, "不存在的静态资源必须 404")

    # ---- /api/stream（G2 SSE 通道连通）----
    def test_stream_requires_project_400(self):
        code, _, _ = self.get("/api/stream")
        self.assertEqual(code, 400, "缺 project 应 400")

    def test_stream_hello_frame(self):
        import socket
        s = socket.create_connection(("127.0.0.1", self.port), timeout=10)
        try:
            s.sendall(f"GET /api/stream?project=P-W3 HTTP/1.0\r\nHost: x\r\n\r\n".encode())
            s.settimeout(20)
            buf = b""
            while b'"hello"' not in buf:
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf += chunk
            text = buf.decode("utf-8", errors="replace")
            self.assertIn("text/event-stream", text, "SSE 内容类型")
            self.assertIn('"hello": true', text, "首帧 hello")
            self.assertIn('"seq":', text, "hello 带 seq 游标")
            self.assertIn("P-W3", text, "hello 回显 project")
        finally:
            s.close()

    # ---- 关联性：事件流→计划快照 同源（state 一致）----
    def test_plan_api_and_events_same_state(self):
        code, _, body = self.get("/api/plan?project=P-W3")
        self.assertEqual(code, 200)
        plan = json.loads(body.decode("utf-8"))
        self.assertEqual(plan["total"], 2)
        self.assertEqual(plan["done"], 1)
        self.assertEqual([t["id"] for t in plan["tasks"]], ["T-W3A", "T-W3B"])
        self.assertEqual([t["editable"] for t in plan["tasks"]], [True, False],
                         "editable 应与状态机门一致（DRAFT 可改 / DONE 不可）")
        code, _, body = self.get("/api/events?since=0")
        ev = json.loads(body.decode("utf-8"))
        tids = {e["taskId"] for e in ev["events"]}
        self.assertIn("T-W3A", tids, "事件流与计划应共享同一状态源")


if __name__ == "__main__":
    unittest.main(verbosity=2)

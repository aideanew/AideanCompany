# -*- coding: utf-8 -*-
"""v3 新增函数的冒烟脚本：只读内存调用 + 写一条 test 事件（事后清理）。"""
import importlib.util
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

spec = importlib.util.spec_from_file_location(
    "c", r"E:\Code\AideanCompany\fleet\console\console.py")
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)

r = c.launch_resolve("P-004", kickoff={"mode": "plan", "port": "3333"})
print("resolve ok=", r["ok"], "| mode=", r["mode"], "| ui=", r.get("ui_url"),
      "| src=", r.get("profile_source"), "| missing=", r.get("missing"))
print("pool_health entries=", len(r.get("model_pool_health") or []))
print("plan rows=", len(r.get("plan") or []))

ok, msg = c.launch_event({"project": "P-004", "phase": "smoke",
                         "detail": "launcher smoke, delete me",
                         "role": "worker-b", "cli": "claude",
                         "model": "claude-default", "percent": "0"})
print("event:", ok, msg)

ev = c.read_events(project="P-004", since=0, limit=5)
last = ev["events"][-1]
print("last action=", last["action"], "| phase=", last.get("phase"),
      "| cli=", last.get("cli"), "| model=", last.get("model"))

# 清理：删掉刚写的 smoke 行（audit.log 末尾一行）
p = c.AUDIT_FILE
lines = p.read_text(encoding="utf-8").splitlines()
if lines and "launcher smoke, delete me" in lines[-1]:
    p.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    print("smoke line cleaned")
else:
    print("WARN: smoke line not at tail, left untouched")

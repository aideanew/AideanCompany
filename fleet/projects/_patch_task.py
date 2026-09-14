import json, sys
T = r"E:\Code\AideanCompany\fleet\console\state\tasks.json"
t = json.load(open(T, encoding="utf-8"))
def trans(tid, new_state, actor, detail):
    TRANS = {"DRAFT": {"ASSIGNED"}, "ASSIGNED": {"DOING", "FAILED"}, "DOING": {"SUBMITTED", "FAILED"},
             "SUBMITTED": {"REVIEWING", "REWORK"}, "REVIEWING": {"DONE", "PARTIAL", "REWORK", "BLOCKED"},
             "REWORK": {"ASSIGNED"}, "PARTIAL": {"ASSIGNED", "DONE"}, "BLOCKED": {"ASSIGNED", "DONE"},
             "FAILED": {"ASSIGNED", "DONE"}, "DONE": set()}
    task = next((x for x in t["tasks"] if x["id"] == tid))
    if new_state not in TRANS.get(task["state"], set()):
        print(f"ILLEGAL {task['state']} -> {new_state}"); sys.exit(1)
    old = task["state"]; task["state"] = new_state
    ts = "2026-09-13 " + sys.argv[2] if len(sys.argv) > 2 else "2026-09-13 23:00:00"
    task.setdefault("history", []).append({"ts": ts, "from": old, "to": new_state, "actor": actor, "detail": detail})
    json.dump(t, open(T, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"{tid} {old} -> {new_state} ok")
trans(sys.argv[1], sys.argv[3], sys.argv[4], sys.argv[5])

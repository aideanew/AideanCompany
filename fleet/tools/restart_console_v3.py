# -*- coding: utf-8 -*-
"""
一键启动完整舰队栈（v3 适配层）：控制台(5000) + Manager(9900) + 全员角色网关 + CLI 探活。
替换旧 restart_console_v3.py 的“只重启控制台”职责；无旧进程则不杀，幂等。
探活报告 CLI 最高权限启动行（用户口径：一律 --dangerously-skip-permissions 级）。
用法：python fleet/tools/restart_console_v3.py            # 全栈启动+探活
      python fleet/tools/restart_console_v3.py --console-only   # 仅控制台
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

EXPECTED_VERSION = "3.1.0-launchbus"
CONSOLE = Path(r"E:\Code\AideanCompany\fleet\console\console.py")
HERMES_BIN = shutil.which("hermes") or "hermes"
BASE = "http://127.0.0.1:5000"

sys.stdout.reconfigure(encoding="utf-8")


def http(path, timeout=8):
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return 0, {"error": str(e)[:120]}


def console_running():
    code, body = http("/api/health", 3)
    return isinstance(body, dict) and body.get("version") == EXPECTED_VERSION


def find_console_pids():
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
          "Where-Object { $_.CommandLine -like '*console.py*' } | "
          "Select-Object -ExpandProperty ProcessId")
    out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                         capture_output=True, text=True).stdout.split()
    return [p for p in out if p.isdigit()]


def spawn(cmd, log_name, cwd=None):
    log = open(Path(r"E:\Code\AideanCompany\fleet\console\logs") / log_name, "ab")
    return subprocess.Popen(cmd, cwd=str(cwd) if cwd else None,
                            stdout=log, stderr=subprocess.STDOUT,
                            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                            | subprocess.DETACHED_PROCESS)


def main():
    console_only = "--console-only" in sys.argv
    # 1) 控制台：已在跑就复用，否则拉起
    if console_running():
        print("[1/4] 控制台已是 v3，复用（不重启）")
    else:
        for pid in find_console_pids():
            subprocess.run(["taskkill", "/PID", pid, "/T", "/F"], capture_output=True)
            print(f"      已停旧控制台 pid={pid}")
        spawn([sys.executable, str(CONSOLE)], "console_v3.out")
        print(f"[1/4] 控制台启动中（日志 console/logs/console_v3.out）…")
        for _ in range(30):
            time.sleep(1)
            if console_running():
                break
        print(f"      /api/health: {'OK ' + EXPECTED_VERSION if console_running() else 'FAIL'}")
        if not console_running():
            return 1

    # 2) Manager + 角色（走 hermes 原生命令，幂等）
    if not console_only:
        print("[2/4] hermes gateway start（Manager 9900，已起会复用）")
        subprocess.run([HERMES_BIN, "gateway", "start"], capture_output=True, timeout=120)
        sys.path.insert(0, str(CONSOLE.parent))
        import importlib.util as _ilu
        spec = _ilu.spec_from_file_location("_c", str(CONSOLE))
        _c = _ilu.module_from_spec(spec)
        spec.loader.exec_module(_c)
        roster = _c.roster()
        started = []
        for x in roster.get("roles", []):
            ok, msg = _c.start_role(x["id"])
            started.append((x["id"], x["port"], ok, msg))
        for rid, port, ok, msg in started:
            print(f"      {rid}:{port} {'OK' if ok else 'FAIL'} ({msg})")

    # 3) 模型池探活（只读，写 state/model_pool_state.json）
    print("[3/4] 模型池探活")
    subprocess.run([sys.executable, str(Path(r"E:\Code\AideanCompany\fleet\tools\probe_pool.py"))])
    try:
        st = json.loads(Path(r"E:\Code\AideanCompany\fleet\console\state"
                             / "model_pool_state.json").read_text(encoding="utf-8"))
        for pid, e in st["providers"].items():
            print(f"      {pid:<11} {e['status']:<12} prio={e['priority']} {e.get('detail', '')}")
    except Exception as e:
        print(f"      读池状态失败: {e}")

    # 4) CLI 探活 + 最高权限启动行打印
    print("[4/4] CLI 探活（最高权限启动口径）")
    clis = [("claude", ["claude", "--version"],
             "claude --dangerously-skip-permissions"),
            ("codex", ["codex", "--version"],
             "codex --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check"),
            ("opencode", ["opencode", "--version"],
             "opencode run --dangerously-skip-permissions")]
    for name, ver_cmd, launch_line in clis:
        r = subprocess.run(ver_cmd, capture_output=True, text=True, timeout=60)
        v = (r.stdout or r.stderr or "").strip().splitlines()
        print(f"      {name:<9} {'OK ' + (v[0] if v else '?') if r.returncode == 0 else 'FAIL'}")
        print(f"                启动行: {launch_line}")
    print("完成。派工提示词经 fleet-launch 渲染；进度写 POST /api/launch-event；报告读 /api/launch-event。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

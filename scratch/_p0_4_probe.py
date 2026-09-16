# -*- coding: utf-8 -*-
"""P0-4 行为验证：超时必须整树终止（父+孙），exit_code=124。

用「心跳文件」判定孙进程生死，避免 tasklist 的 GBK 编码问题。
"""
import sys
import time
from pathlib import Path

ROOT = Path(r"E:\Code\AideanCompany")
sys.path.insert(0, str(ROOT / "fleet" / "runner"))
from cli_runner import execute_task_pack

ev = ROOT / "fleet" / "console" / "state" / "evidence" / "_p0_4_probe"
ev.mkdir(parents=True, exist_ok=True)
hb = ev / "_hb.txt"
if hb.exists():
    hb.unlink()

(ev / "_grandchild.py").write_text(
    "import time,sys\n"
    f"HB=r'{hb}'\n"
    "while True:\n"
    "    open(HB,'w').write(str(time.time()))\n"
    "    time.sleep(0.3)\n", encoding="utf-8")

(ev / "_parent.py").write_text(
    "import subprocess,sys,time\n"
    f"subprocess.Popen([sys.executable, r'{ev / '_grandchild.py'}'])\n"
    "time.sleep(600)\n", encoding="utf-8")

py = sys.executable
registry = {"fake": {"binary": "python",
                     "command_template": f'"{py}" "{ev / "_parent.py"}" --model {{MODEL}}'}}
pack = {"id": "_P0PROBE", "title": "p0-4 probe", "workdir": str(ev),
        "detail": "synthetic", "verify_cmd": "echo ok",
        "executor": {"cli": "fake", "model": "probe"}}

t0 = time.time()
res = execute_task_pack(pack, registry, ev, timeout_sec=3)
dt = time.time() - t0

# 判定 1：返回值
r_ok = (res.exit_code == 124 and res.timed_out is True and res.ok is False and dt < 20)
print(f"[P0-4] timed_out={res.timed_out} exit_code={res.exit_code} ok={res.ok} 用时={dt:.1f}s -> {'OK' if r_ok else 'FAIL'}")
print(f"        error={res.error!r}")

# 判定 2：孙进程是否真的死了（心跳停更）
h1 = hb.read_text() if hb.exists() else "<none>"
time.sleep(1.5)
h2 = hb.read_text() if hb.exists() else "<none>"
alive = (h1 != h2) and hb.exists()
print(f"[P0-4] 心跳 h1={h1[:18]} h2={h2[:18]} 孙进程存活={alive} -> {'FAIL(未整树杀)' if alive else 'OK(整树已杀)'}")

# 判定 3：残留清理
import subprocess
leftover = subprocess.run(["powershell", "-NoProfile", "-Command",
    r"(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
    r"Where-Object { $_.CommandLine -like '*_parent.py*' -or $_.CommandLine -like '*_grandchild.py*' }).Count"],
    capture_output=True, text=True)
print("[P0-4] 残留 _parent/_grandchild 进程数 =", (leftover.stdout or "").strip() or "?")

final = r_ok and not alive
print("[P0-4]", "PASS" if final else "FAIL")
print("SUMMARY:", "ALL PASS" if final else "FAIL")

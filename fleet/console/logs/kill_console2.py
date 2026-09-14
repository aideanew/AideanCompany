# -*- coding: utf-8 -*-
"""停止卡死的控制台进程（带错误输出）"""
import subprocess
import sys

try:
    out = subprocess.run(
        ['powershell', '-NoProfile', '-Command',
         "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'console.py' } | ForEach-Object { $_.ProcessId }"],
        capture_output=True)
    print('rc:', out.returncode)
    print('stdout:', out.stdout.decode('gbk', errors='replace'))
    print('stderr:', out.stderr.decode('gbk', errors='replace'))
    pids = [p.strip() for p in out.stdout.decode('gbk', errors='replace').split() if p.strip()]
    print('匹配进程:', pids)
    for pid in pids:
        r = subprocess.call(f'taskkill /PID {pid} /T /F', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print('killed', pid, 'rc=', r)
    print('完成')
except Exception as e:
    print('异常:', repr(e))
    sys.exit(1)

# -*- coding: utf-8 -*-
"""停止卡死的控制台进程（按命令行匹配 console.py）"""
import subprocess

out = subprocess.run(
    ['powershell', '-NoProfile', '-Command',
     "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'console.py' } | ForEach-Object { $_.ProcessId }"],
    capture_output=True).stdout.decode('gbk', errors='replace')
pids = [p.strip() for p in out.split() if p.strip()]
for pid in pids:
    r = subprocess.call(f'taskkill /PID {pid} /T /F', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print('killed', pid, 'rc=', r)
print('剩余 console 进程:', pids or '无')

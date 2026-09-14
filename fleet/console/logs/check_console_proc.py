# -*- coding: utf-8 -*-
"""检查 console 进程"""
import subprocess
out = subprocess.run(
    ['powershell', '-NoProfile', '-Command',
     "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'console.py' } | ForEach-Object { $_.ProcessId.ToString() + ' | ' + $_.CreationDate.ToString('HH:mm:ss') }"],
    capture_output=True)
print('console 进程:', out.stdout.decode('gbk', errors='replace') or '无', '| stderr:', out.stderr.decode('gbk', errors='replace')[:200])

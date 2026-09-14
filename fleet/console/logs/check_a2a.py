# -*- coding: utf-8 -*-
"""检查 a2a hermes 进程活动"""
import subprocess

out = subprocess.run(
    ['powershell', '-NoProfile', '-Command',
     "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'a2a' -and $_.Name -eq 'hermes.exe' } | ForEach-Object { $_.ProcessId.ToString() + ' | ' + $_.CreationDate.ToString('HH:mm:ss') }"],
    capture_output=True)
print('活跃 a2a hermes 进程:', out.stdout.decode('gbk', errors='replace') or '无')

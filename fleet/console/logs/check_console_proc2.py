# -*- coding: utf-8 -*-
"""精确检查 console 相关进程命令行"""
import subprocess
out = subprocess.run(
    ['powershell', '-NoProfile', '-Command',
     "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'console' } | ForEach-Object { $_.ProcessId.ToString() + ' | ' + $_.CommandLine.Substring(0, [Math]::Min(120, $_.CommandLine.Length)) }"],
    capture_output=True)
print(out.stdout.decode('gbk', errors='replace') or '无')

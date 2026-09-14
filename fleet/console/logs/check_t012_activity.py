# -*- coding: utf-8 -*-
"""检查 T-012 a2a 活动"""
import subprocess
import urllib.request

out = subprocess.run(
    ['powershell', '-NoProfile', '-Command',
     "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'a2a' -and $_.Name -eq 'hermes.exe' } | ForEach-Object { $_.ProcessId.ToString() + ' | ' + $_.CreationDate.ToString('HH:mm:ss') }"],
    capture_output=True)
print('活跃 a2a:', out.stdout.decode('gbk', errors='replace') or '无')

# 检查是否已经测试数据落盘（be-3 是否在跑）
import pathlib
ev = pathlib.Path(r'E:\Code\AideanBot\.workbuddy\evidence')
recent = sorted(ev.glob('*'), key=lambda p: p.stat().st_mtime, reverse=True)[:6]
print('最近证据文件:')
for p in recent:
    print(' ', p.name, datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime('%H:%M:%S'))
import datetime

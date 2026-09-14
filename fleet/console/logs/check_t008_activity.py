# -*- coding: utf-8 -*-
"""检查 a2a 会话活动与 worker-b 网关"""
import subprocess
import urllib.request

out = subprocess.run(
    ['powershell', '-NoProfile', '-Command',
     "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'a2a' -and $_.Name -eq 'hermes.exe' } | ForEach-Object { $_.ProcessId.ToString() + ' | ' + $_.CreationDate.ToString('HH:mm:ss') }"],
    capture_output=True)
print('活跃 a2a:', out.stdout.decode('gbk', errors='replace') or '无')

# worker-b 网关
try:
    r = urllib.request.urlopen('http://127.0.0.1:9902/.well-known/agent-card.json', timeout=4)
    print('worker-b 9902:', r.status)
except Exception as e:
    print('worker-b 9902:', str(e)[:50])

# Manager 9900
try:
    r = urllib.request.urlopen('http://127.0.0.1:9900/.well-known/agent-card.json', timeout=4)
    print('Manager 9900:', r.status)
except Exception as e:
    print('Manager 9900:', str(e)[:50])

# 检查后端改动时间（worker-b 是否在写文件）
import pathlib
kb = pathlib.Path(r'E:\Code\AideanBot\backend\app\services\kb.py')
import os
print('kb.py 最后修改:', __import__('datetime').datetime.fromtimestamp(kb.stat().st_mtime).strftime('%H:%M:%S'))

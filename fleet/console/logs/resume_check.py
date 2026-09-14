# -*- coding: utf-8 -*-
"""断点恢复：检查控制台与任务状态"""
import json
import subprocess
import urllib.request

# 1) 控制台健康
try:
    r = urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=6)
    print('5000:', r.status)
except Exception as e:
    print('5000: DOWN', str(e)[:80])

# 2) 任务状态
try:
    d = json.load(open(r'E:\Code\AideanCompany\fleet\console\state\tasks.json', encoding='utf-8'))
    print('--- 任务状态 ---')
    for t in d['tasks']:
        if t['id'] >= 'T-003':
            print(t['id'], '|', t['assignee'], '|', t['state'], '| report:', len(t.get('report', '')), 'B |', t.get('state_note', '')[:40])
except Exception as e:
    print('tasks.json 读取失败:', str(e)[:80])

# 3) 进程检查
out = subprocess.run(
    ['powershell', '-NoProfile', '-Command',
     "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'worker-a' -and $_.Name -eq 'hermes.exe' } | ForEach-Object { $_.ProcessId.ToString() + ' | ' + $_.CreationDate.ToString('HH:mm:ss') }"],
    capture_output=True).stdout.decode('gbk', errors='replace')
print('worker-a 网关进程:', out or '无')

out2 = subprocess.run(
    ['powershell', '-NoProfile', '-Command',
     "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'console.py' } | ForEach-Object { $_.ProcessId.ToString() }"],
    capture_output=True).stdout.decode('gbk', errors='replace')
print('console 进程:', out2 or '无')

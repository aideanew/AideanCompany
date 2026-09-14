# -*- coding: utf-8 -*-
"""脱离会话启动控制台（与角色网关同款机制）"""
import subprocess
import os
import time
import urllib.request

DETACHED = 0x00000008 | 0x00000200
log = open(r'E:\Code\AideanCompany\fleet\console\logs\console-detached.log', 'ab')
p = subprocess.Popen(
    [r'C:\Program Files\Python313\python.exe', r'E:\Code\AideanCompany\fleet\console\console.py'],
    stdout=log, stderr=subprocess.STDOUT, creationflags=DETACHED, close_fds=True)
print('控制台已脱离会话启动 pid=', p.pid)

# 等待健康
ok = False
for i in range(12):
    time.sleep(5)
    try:
        r = urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=4)
        print(f'[{i*5}s] 5000: {r.status}')
        ok = True
        break
    except Exception as e:
        print(f'[{i*5}s] 未就绪: {str(e)[:60]}')
print('控制台就绪' if ok else '控制台启动失败，查看日志')
if not ok:
    try:
        print(open(r'E:\Code\AideanCompany\fleet\console\logs\console-detached.log', 'r', encoding='utf-8', errors='replace').read()[-1500:])
    except Exception as e:
        print('读日志失败:', e)

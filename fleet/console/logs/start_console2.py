# -*- coding: utf-8 -*-
"""DETACHED 启动控制台并轮询端口就绪"""
import subprocess
import time
import urllib.request

DETACHED = 0x00000008 | 0x00000200
log = open(r'E:\Code\AideanCompany\fleet\console\logs\console-detached.log', 'ab')
p = subprocess.Popen(
    [r'C:\Program Files\Python313\python.exe', r'E:\Code\AideanCompany\fleet\console\console.py'],
    stdout=log, stderr=subprocess.STDOUT, creationflags=DETACHED, close_fds=True)
print('pid:', p.pid, flush=True)

for i in range(15):
    time.sleep(4)
    try:
        r = urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=3)
        print(f'[{i*4}s] 5000 OK status={r.status}', flush=True)
        break
    except Exception as e:
        print(f'[{i*4}s] wait {str(e)[:40]}', flush=True)
print('done', flush=True)

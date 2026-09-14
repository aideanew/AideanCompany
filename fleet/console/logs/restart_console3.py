# -*- coding: utf-8 -*-
"""单实例 DETACHED 启动控制台，结果写日志文件"""
import subprocess
import time
import socket

LOG = r'E:\Code\AideanCompany\fleet\console\logs\final_restart_result.txt'
with open(LOG, 'w', encoding='utf-8') as f:
    f.write('start\n')
    f.flush()

DETACHED = 0x00000008 | 0x00000200
log = open(r'E:\Code\AideanCompany\fleet\console\logs\console-detached.log', 'ab')
p = subprocess.Popen(
    [r'C:\Program Files\Python313\python.exe', r'E:\Code\AideanCompany\fleet\console\console.py'],
    stdout=log, stderr=subprocess.STDOUT, creationflags=DETACHED, close_fds=True)

with open(LOG, 'a', encoding='utf-8') as f:
    f.write(f'pid: {p.pid}\n')
    f.flush()

for i in range(15):
    time.sleep(4)
    try:
        s = socket.create_connection(('127.0.0.1', 5000), timeout=5)
        s.sendall(b'GET /api/health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n')
        data = b''
        s.settimeout(5)
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
        s.close()
        status = data.split(b'\r\n')[0].decode('utf-8', errors='replace')
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(f'[{i*4}s] {status}\n')
            f.flush()
        if '200' in status:
            with open(LOG, 'a', encoding='utf-8') as f:
                f.write('READY\n')
            break
    except Exception as e:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(f'[{i*4}s] wait {str(e)[:50]}\n')
            f.flush()

with open(LOG, 'a', encoding='utf-8') as f:
    f.write('done\n')

# -*- coding: utf-8 -*-
"""对照实验：Popen pid vs netstat pid + 长超时 curl + 读取横幅"""
import subprocess
import time
import urllib.request
import socket

p = subprocess.Popen(
    [r'C:\Program Files\Python313\python.exe', r'E:\Code\AideanCompany\fleet\console\console.py'],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
print('Popen pid:', p.pid, flush=True)
time.sleep(8)

out = subprocess.run(['netstat', '-ano'], capture_output=True).stdout.decode('gbk', errors='replace')
lines = [l for l in out.splitlines() if ':5000' in l]
print('--- netstat :5000 ---')
for l in lines[:5]:
    print(l)
    parts = l.split()
    print('  → LISTENING pid:', parts[-1] if parts else '?')

# 用 socket 直接连（10 秒超时）
try:
    s = socket.create_connection(('127.0.0.1', 5000), timeout=10)
    s.sendall(b'GET /api/health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n')
    data = b''
    s.settimeout(10)
    try:
        while True:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
    except socket.timeout:
        print('socket 读超时，已收', len(data), 'B')
    s.close()
    print('socket 响应:', data[:200].decode('utf-8', errors='replace'))
except Exception as e:
    print('socket 连接失败:', str(e)[:100])

p.terminate()
try:
    out2, _ = p.communicate(timeout=5)
    print('--- 进程输出 ---')
    print(out2.decode('utf-8', errors='replace')[-800:])
except Exception as e:
    print('读输出失败:', e)

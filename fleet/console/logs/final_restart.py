# -*- coding: utf-8 -*-
"""最终清理：杀全部 5000 监听 → 单实例 DETACHED 启动 → socket 直连验证"""
import subprocess
import time
import socket

# 1) 杀全部 5000 监听进程
out = subprocess.run(['netstat', '-ano'], capture_output=True).stdout.decode('gbk', errors='replace')
zombies = set()
for l in out.splitlines():
    if ':5000' in l and 'LISTENING' in l:
        zombies.add(l.split()[-1].strip())
print('5000 监听进程:', zombies)
for pid in zombies:
    subprocess.call(f'taskkill /PID {pid} /T /F', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print('killed', pid)
# 再杀所有 console.py 残留
out = subprocess.run(
    ['powershell', '-NoProfile', '-Command',
     "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'console.py' } | ForEach-Object { $_.ProcessId }"],
    capture_output=True).stdout.decode('gbk', errors='replace')
for pid in [p.strip() for p in out.split() if p.strip()]:
    subprocess.call(f'taskkill /PID {pid} /T /F', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print('清理 console.py 残留', pid)
time.sleep(3)

# 2) 确认释放
out = subprocess.run(['netstat', '-ano'], capture_output=True).stdout.decode('gbk', errors='replace')
still = [l for l in out.splitlines() if ':5000' in l]
print('释放后残留:', still or '无')

# 3) 单实例 DETACHED 启动
DETACHED = 0x00000008 | 0x00000200
log = open(r'E:\Code\AideanCompany\fleet\console\logs\console-detached.log', 'ab')
p = subprocess.Popen(
    [r'C:\Program Files\Python313\python.exe', r'E:\Code\AideanCompany\fleet\console\console.py'],
    stdout=log, stderr=subprocess.STDOUT, creationflags=DETACHED, close_fds=True)
print('新实例 pid:', p.pid)

# 4) socket 直连轮询（规避 curl 代理）
for i in range(12):
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
        print(f'[{i*4}s] socket 响应: {status}')
        if '200' in status:
            print('控制台就绪 ✅')
            break
    except Exception as e:
        print(f'[{i*4}s] wait {str(e)[:50]}')

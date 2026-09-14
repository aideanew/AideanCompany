# -*- coding: utf-8 -*-
"""杀掉 5000 端口僵尸进程并干净重启控制台"""
import subprocess
import time
import urllib.request
import socket

# 1) 找出 5000 监听进程
out = subprocess.run(['netstat', '-ano'], capture_output=True).stdout.decode('gbk', errors='replace')
zombie = set()
for l in out.splitlines():
    if ':5000' in l and 'LISTENING' in l:
        zombie.add(l.split()[-1].strip())
print('5000 监听进程:', zombie)

# 2) 全杀（包括残留 console.py 进程）
for pid in list(zombie):
    subprocess.call(f'taskkill /PID {pid} /T /F', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print('killed 僵尸', pid)
time.sleep(2)

# 3) 再次确认端口已释放
out = subprocess.run(['netstat', '-ano'], capture_output=True).stdout.decode('gbk', errors='replace')
still = [l for l in out.splitlines() if ':5000' in l]
print('释放后残留:', still or '无')

# 4) 干净启动（DETACHED）
DETACHED = 0x00000008 | 0x00000200
log = open(r'E:\Code\AideanCompany\fleet\console\logs\console-detached.log', 'ab')
p = subprocess.Popen(
    [r'C:\Program Files\Python313\python.exe', r'E:\Code\AideanCompany\fleet\console\console.py'],
    stdout=log, stderr=subprocess.STDOUT, creationflags=DETACHED, close_fds=True)
print('新实例 pid:', p.pid)

# 5) 轮询就绪
for i in range(12):
    time.sleep(4)
    try:
        r = urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=3)
        print(f'[{i*4}s] 5000 OK status={r.status}')
        break
    except Exception as e:
        print(f'[{i*4}s] wait {str(e)[:40]}')

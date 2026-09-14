# -*- coding: utf-8 -*-
"""决定性测试：前台启动 console.py，6 秒后 netstat + curl 双验证"""
import subprocess
import time
import urllib.request

p = subprocess.Popen(
    [r'C:\Program Files\Python313\python.exe', r'E:\Code\AideanCompany\fleet\console\console.py'],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
time.sleep(6)

# 1) netstat 查 5000
out = subprocess.run(['netstat', '-ano'], capture_output=True).stdout.decode('gbk', errors='replace')
lines = [l for l in out.splitlines() if ':5000' in l]
print('--- netstat :5000 ---')
print('\n'.join(lines[:5]) or '无监听')

# 2) curl 本地
try:
    r = urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=4)
    print('curl /api/health:', r.status)
except Exception as e:
    print('curl 失败:', str(e)[:60])

# 3) 读进程输出（非阻塞）
p.terminate()
try:
    out2, _ = p.communicate(timeout=5)
    print('--- 进程输出 ---')
    print(out2.decode('utf-8', errors='replace')[-1200:])
except Exception as e:
    print('读输出失败:', e)

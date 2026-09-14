# -*- coding: utf-8 -*-
"""重启 worker-a 网关 + 检查各网关在线状态"""
import subprocess
import time
import urllib.request

# 1) 停 worker-a 网关（按命令行匹配）
out = subprocess.run(
    ['powershell', '-NoProfile', '-Command',
     "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'worker-a' -and $_.Name -eq 'hermes.exe' } | ForEach-Object { $_.ProcessId }"],
    capture_output=True).stdout.decode('gbk', errors='replace')
pids = [p.strip() for p in out.split() if p.strip()]
print('worker-a 网关进程:', pids)
for pid in pids:
    subprocess.call(f'taskkill /PID {pid} /T /F', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print('killed', pid)
time.sleep(2)

# 2) 重新启动 worker-a 网关（脱离会话）
DETACHED = 0x00000008 | 0x00000200
log = open(r'E:\Code\AideanCompany\fleet\console\logs\worker-a-gateway.log', 'ab')
env = dict(__import__('os').environ, HERMES_ACCEPT_HOOKS='1')
p = subprocess.Popen(
    ['hermes', '-p', 'worker-a', 'gateway', 'run'],
    stdout=log, stderr=subprocess.STDOUT, creationflags=DETACHED, close_fds=True, env=env)
print('worker-a 网关启动 pid:', p.pid)

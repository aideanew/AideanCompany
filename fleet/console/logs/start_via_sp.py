# -*- coding: utf-8 -*-
"""用 Start-Process 启动控制台（独立进程），再 socket 验证"""
import subprocess
import time
import socket

# 1) 杀全部 5000 监听 + console.py
out = subprocess.run(['netstat', '-ano'], capture_output=True).stdout.decode('gbk', errors='replace')
zombies = set()
for l in out.splitlines():
    if ':5000' in l and 'LISTENING' in l:
        zombies.add(l.split()[-1].strip())
print('杀 5000:', zombies)
for pid in zombies:
    subprocess.call(f'taskkill /PID {pid} /T /F', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)

# 2) Start-Process 启动（独立于本进程，不共享句柄）
ps_cmd = ("Start-Process -FilePath 'C:\\Program Files\\Python313\\python.exe' "
          "-ArgumentList 'E:\\Code\\AideanCompany\\fleet\\console\\console.py' "
          "-RedirectStandardOutput 'E:\\Code\\AideanCompany\\fleet\\console\\logs\\console-sp.log' "
          "-RedirectStandardError 'E:\\Code\\AideanCompany\\fleet\\console\\logs\\console-sp-err.log' "
          "-WindowStyle Hidden -PassThru | Select-Object -ExpandProperty Id")
r = subprocess.run(['powershell', '-NoProfile', '-Command', ps_cmd], capture_output=True)
print('Start-Process rc:', r.returncode, 'pid:', r.stdout.decode('gbk', errors='replace').strip())

# 3) socket 轮询
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
        print(f'[{i*4}s] socket: {status}')
        if '200' in status:
            print('READY')
            break
    except Exception as e:
        print(f'[{i*4}s] wait {str(e)[:50]}')

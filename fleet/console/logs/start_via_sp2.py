# -*- coding: utf-8 -*-
"""Start-Process 启动控制台，结果写文件"""
import subprocess
import time
import socket

LOG = r'E:\Code\AideanCompany\fleet\console\logs\sp_result.txt'
def w(msg):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(msg + '\n')
        f.flush()

open(LOG, 'w').close()

# 1) 杀全部 5000 监听
out = subprocess.run(['netstat', '-ano'], capture_output=True).stdout.decode('gbk', errors='replace')
zombies = set()
for l in out.splitlines():
    if ':5000' in l and 'LISTENING' in l:
        zombies.add(l.split()[-1].strip())
w('杀 5000: ' + str(zombies))
for pid in zombies:
    subprocess.call(f'taskkill /PID {pid} /T /F', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)

# 2) Start-Process
ps_cmd = ("Start-Process -FilePath 'C:\\Program Files\\Python313\\python.exe' "
          "-ArgumentList 'E:\\Code\\AideanCompany\\fleet\\console\\console.py' "
          "-RedirectStandardOutput 'E:\\Code\\AideanCompany\\fleet\\console\\logs\\console-sp.log' "
          "-RedirectStandardError 'E:\\Code\\AideanCompany\\fleet\\console\\logs\\console-sp-err.log' "
          "-WindowStyle Hidden -PassThru | Select-Object -ExpandProperty Id")
r = subprocess.run(['powershell', '-NoProfile', '-Command', ps_cmd], capture_output=True)
pid_out = r.stdout.decode('gbk', errors='replace').strip()
w(f'Start-Process rc={r.returncode} pid={pid_out}')

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
        w(f'[{i*4}s] socket: {status}')
        if '200' in status:
            w('READY')
            break
    except Exception as e:
        w(f'[{i*4}s] wait {str(e)[:50]}')
w('done')

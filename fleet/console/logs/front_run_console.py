# -*- coding: utf-8 -*-
"""前台启动控制台 8 秒抓错（验证真实报错）"""
import subprocess
import time

p = subprocess.Popen(
    [r'C:\Program Files\Python313\python.exe', r'E:\Code\AideanCompany\fleet\console\console.py'],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
time.sleep(8)
if p.poll() is None:
    print('进程存活（8秒未崩）— 正在监听？')
    p.terminate()
else:
    out, _ = p.communicate()
    print('进程退出 rc=', p.returncode)
    print(out.decode('utf-8', errors='replace')[-2000:])

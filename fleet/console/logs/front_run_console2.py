# -*- coding: utf-8 -*-
"""前台运行控制台 20 秒，捕获完整输出"""
import subprocess
import time

p = subprocess.Popen(
    [r'C:\Program Files\Python313\python.exe', r'E:\Code\AideanCompany\fleet\console\console.py'],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
time.sleep(20)
if p.poll() is None:
    print('20秒后进程仍存活 — 尝试读输出（非阻塞）')
    import msvcrt
    # terminate
    p.terminate()
    try:
        out, _ = p.communicate(timeout=5)
        print('--- 完整输出 ---')
        print(out.decode('utf-8', errors='replace')[-3000:])
    except Exception as e:
        print('读输出失败:', e)
else:
    out, _ = p.communicate()
    print('进程退出 rc=', p.returncode)
    print(out.decode('utf-8', errors='replace')[-3000:])

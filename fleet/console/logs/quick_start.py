# -*- coding: utf-8 -*-
"""快速启动控制台（Popen 立即返回，不等待）"""
import subprocess

DETACHED = 0x00000008 | 0x00000200
log = open(r'E:\Code\AideanCompany\fleet\console\logs\console-detached.log', 'ab')
p = subprocess.Popen(
    [r'C:\Program Files\Python313\python.exe', r'E:\Code\AideanCompany\fleet\console\console.py'],
    stdout=log, stderr=subprocess.STDOUT, creationflags=DETACHED, close_fds=True)
print('started pid:', p.pid)

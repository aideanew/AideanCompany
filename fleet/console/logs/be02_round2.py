# -*- coding: utf-8 -*-
"""BE-02 第二轮：pytest 全量（含新测试）"""
import subprocess

PY = r'E:\Code\AideanBot\backend\.venv\Scripts\python.exe'
WD = r'E:\Code\AideanBot\backend'
r = subprocess.run([PY, '-m', 'pytest', '-q', '--no-header', '--maxfail=3'],
                   capture_output=True, text=True, encoding='utf-8', errors='replace',
                   cwd=WD, timeout=600)
print('rc=', r.returncode)
print((r.stdout + r.stderr)[-2500:])

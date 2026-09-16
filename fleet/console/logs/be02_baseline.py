# -*- coding: utf-8 -*-
"""BE-02 基线：跑当前全量 pytest 记录基线"""
import subprocess

PY = r'E:\Code\AideanBot\backend\.venv\Scripts\python.exe'
WD = r'E:\Code\AideanBot\backend'
r = subprocess.run([PY, '-m', 'pytest', '-q', '--no-header', '--maxfail=1'],
                   capture_output=True, text=True, encoding='utf-8', errors='replace',
                   cwd=WD, timeout=600)
print('rc=', r.returncode)
print((r.stdout + r.stderr)[-1500:])

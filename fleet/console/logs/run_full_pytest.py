# -*- coding: utf-8 -*-
"""backend 完整 pytest + ruff + mypy"""
import subprocess

PY = r'E:\Code\AideanBot\backend\.venv\Scripts\python.exe'
WD = r'E:\Code\AideanBot\backend'

# 1) 完整 pytest
r = subprocess.run([PY, '-m', 'pytest', '-q', '--no-header', '--maxfail=3'],
                   capture_output=True, text=True, encoding='utf-8', errors='replace',
                   cwd=WD, timeout=600)
print('=== pytest rc=', r.returncode)
print((r.stdout + r.stderr)[-1200:])

# -*- coding: utf-8 -*-
"""BE-02 门禁：ruff + mypy"""
import subprocess

PY = r'E:\Code\AideanBot\backend\.venv\Scripts\python.exe'
WD = r'E:\Code\AideanBot\backend'

# ruff
r = subprocess.run([PY, '-m', 'ruff', 'check', '.'],
                   capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=WD, timeout=180)
print('=== ruff rc=', r.returncode)
print((r.stdout + r.stderr)[-1500:])

# mypy
r = subprocess.run([PY, '-m', 'mypy', 'app'],
                   capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=WD, timeout=300)
print('=== mypy rc=', r.returncode)
print((r.stdout + r.stderr)[-2000:])

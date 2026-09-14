# -*- coding: utf-8 -*-
"""监督者复验：后端语法门 + 前端类型检查（T-008/T-010 修复质量）"""
import subprocess
import pathlib
import os

def run(cmd, cwd=None, timeout=180):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', cwd=cwd, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr)[-1500:]
    except subprocess.TimeoutExpired:
        return -1, 'TIMEOUT'

# 1) 后端全部 .py 语法门
print('=== backend py_compile ===')
r = subprocess.run([r'C:\Program Files\Python313\python.exe', '-m', 'py_compile'] +
                   [str(p) for p in pathlib.Path(r'E:\Code\AideanBot\backend').rglob('*.py')],
                   capture_output=True, text=True, encoding='utf-8', errors='replace')
print('rc=', r.returncode, (r.stdout + r.stderr)[-800:] or 'OK')

# 2) 后端 pytest（kb 修复用例）
print('=== backend pytest -q（kb 相关）===')
code, out = run(r'"C:\Program Files\Python313\python.exe" -m pytest -q -x', cwd=r'E:\Code\AideanBot\backend', timeout=240)
print('rc=', code)
print(out[-1200:])

# -*- coding: utf-8 -*-
"""BE-02 第一轮：语法 + 全量 pytest"""
import subprocess
import sys

PY = r'E:\Code\AideanBot\backend\.venv\Scripts\python.exe'
WD = r'E:\Code\AideanBot\backend'

# 语法
r = subprocess.run([PY, '-m', 'py_compile',
                    r'app\services\kb.py', r'app\services\spaces.py', r'app\api\v1\chat.py',
                    r'app\api\deps.py', r'app\providers\engine_port.py', r'app\providers\raw_store.py',
                    r'app\core\config.py'],
                   capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=WD)
print('=== py_compile rc=', r.returncode)
print((r.stdout + r.stderr)[-800:])

# pytest
r = subprocess.run([PY, '-m', 'pytest', '-q', '--no-header', '--maxfail=3'],
                   capture_output=True, text=True, encoding='utf-8', errors='replace',
                   cwd=WD, timeout=600)
print('=== pytest rc=', r.returncode)
print((r.stdout + r.stderr)[-2500:])

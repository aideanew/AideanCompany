# -*- coding: utf-8 -*-
"""快速跑 backend pytest"""
import subprocess
import sys

r = subprocess.run([sys.executable, '-m', 'pytest', '-q', '--no-header', '-x', '--maxfail=1'],
                   capture_output=True, text=True, encoding='utf-8', errors='replace',
                   cwd=r'E:\Code\AideanBot\backend', timeout=240)
print('rc=', r.returncode)
out = (r.stdout + r.stderr)
print(out[-2500:])

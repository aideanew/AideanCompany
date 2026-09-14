# -*- coding: utf-8 -*-
"""监督者复验：后端逐文件 py_compile + pytest 快速"""
import subprocess
import pathlib
import sys

bad = []
files = sorted(pathlib.Path(r'E:\Code\AideanBot\backend').rglob('*.py'))
for p in files:
    r = subprocess.run([sys.executable, '-m', 'py_compile', str(p)],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        bad.append((str(p), (r.stdout + r.stderr)[-300:]))
print(f'=== backend py_compile: {len(files)} 文件, {len(bad)} 失败 ===')
for p, err in bad[:10]:
    print('FAIL:', p)
    print(err)

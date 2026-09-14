# -*- coding: utf-8 -*-
"""收集 AideanBot 改动文件清单（git status + 关键文件修改时间）"""
import subprocess
import pathlib
import datetime

# git status（若有 git）
r = subprocess.run(['git', '-C', r'E:\Code\AideanBot', 'status', '--short'],
                   capture_output=True, text=True, encoding='utf-8', errors='replace')
print('=== git status --short ===')
print(r.stdout[:2000] or '(无输出)')

# 关键文件 mtime
print('=== 关键文件修改时间 ===')
files = [
    r'E:\Code\AideanBot\backend\app\services\kb.py',
    r'E:\Code\AideanBot\backend\app\api\v1\spaces.py',
    r'E:\Code\AideanBot\backend\tests\test_langbot.py',
    r'E:\Code\AideanBot\frontend\app\page.tsx',
    r'E:\Code\AideanBot\frontend\app\chat\page.tsx',
    r'E:\Code\AideanBot\frontend\app\spaces\[id]\page.tsx',
]
for f in files:
    p = pathlib.Path(f)
    if p.exists():
        mt = datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime('%m-%d %H:%M:%S')
        print(f'{mt}  {f}')
    else:
        print(f'缺失: {f}')

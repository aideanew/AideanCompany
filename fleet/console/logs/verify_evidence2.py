# -*- coding: utf-8 -*-
"""监督者复跑关键证据 v2（用 findstr/rg 替代 grep）"""
import subprocess
import pathlib

def read_lines(path, enc='utf-8'):
    try:
        return pathlib.Path(path).read_text(encoding=enc, errors='replace').splitlines()
    except Exception as e:
        return [f'ERR {e}']

# 1) README 知识库计数
t = pathlib.Path(r'E:\Code\AideanBot\README.md').read_text(encoding='utf-8', errors='replace')
print('=== README 知识库命中 ===')
for i, line in enumerate(t.splitlines(), 1):
    if '知识库' in line:
        print(f'{i}: {line[:80]}')

# 2) P0-1 前端 404 判定码
print()
print('=== frontend/app/spaces/[id]/page.tsx 错误码判定 ===')
p = pathlib.Path(r'E:\Code\AideanBot\frontend\app\spaces\[id]\page.tsx')
lines = read_lines(str(p))
for i, line in enumerate(lines, 1):
    if any(k in line for k in ('30101', '10102', '30004', 'setNotFound')):
        print(f'{i}: {line.strip()[:100]}')

# 3) 后端 spaces.py 30004 码位
print()
print('=== backend spaces.py 30004 ===')
p = pathlib.Path(r'E:\Code\AideanBot\backend\app\api\v1\spaces.py')
lines = read_lines(str(p))
for i, line in enumerate(lines, 1):
    if '30004' in line or 'ResourceNotFound' in line:
        print(f'{i}: {line.strip()[:100]}')

# 4) IDOR：kb.py ingest 归属校验
print()
print('=== backend kb.py ingest/status 归属校验（应无 user 比对）===')
p = pathlib.Path(r'E:\Code\AideanBot\backend\app\services\kb.py')
lines = read_lines(str(p))
for i, line in enumerate(lines, 1):
    if 'ingest' in line.lower() or 'get_doc_ingest_status' in line or 'space.user_id' in line or 'user_id' in line:
        print(f'{i}: {line.strip()[:110]}')

# 5) 后端 get_space_view 有归属校验（对照组）
print()
print('=== backend services/spaces.py 归属校验对照 ===')
p = pathlib.Path(r'E:\Code\AideanBot\backend\app\services\spaces.py')
lines = read_lines(str(p))
for i, line in enumerate(lines, 1):
    if 'user_id' in line and ('!=' in line or '==' in line):
        print(f'{i}: {line.strip()[:110]}')

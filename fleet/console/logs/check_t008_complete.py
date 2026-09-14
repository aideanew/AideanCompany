# -*- coding: utf-8 -*-
"""检查 T-008 改动完整性：kb.py/spaces.py/测试用例"""
import pathlib

# 1) kb.py 归属校验完整看
print('=== kb.py ingest_url + get_doc_ingest_status 归属校验 ===')
lines = pathlib.Path(r'E:\Code\AideanBot\backend\app\services\kb.py').read_text(encoding='utf-8').splitlines()
for i in range(108, 215):
    if i <= len(lines):
        l = lines[i-1]
        if 'user_id' in l or 'ingest' in l or 'def ' in l or 'ResourceNotFound' in l or 'space' in l:
            print(f'{i}: {l.strip()[:100]}')

# 2) 测试用例新增
print()
print('=== 测试用例中 30004/IDOR/归属 ===')
import re
for p in pathlib.Path(r'E:\Code\AideanBot\backend\tests').rglob('*.py'):
    txt = p.read_text(encoding='utf-8', errors='replace')
    if '30004' in txt or 'IDOR' in txt or '他人' in txt or 'ownership' in txt.lower() or 'forbidden' in txt.lower():
        print('候选:', p.name)
        for i, line in enumerate(txt.splitlines(), 1):
            if any(k in line for k in ('30004', 'IDOR', '他人', 'ownership', 'forbidden', 'ingest')):
                print(f'  {i}: {line.strip()[:100]}')

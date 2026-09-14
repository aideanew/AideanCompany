# -*- coding: utf-8 -*-
"""确认 worker-a SOUL 白名单 + 检查 T-004/T-008/T-011 详情"""
import json
import pathlib

# 1) worker-a SOUL 白名单
for p in [r'C:\Users\EDY\AppData\Local\hermes\profiles\worker-a\SOUL.md',
          r'C:\Users\Public\Loomy\11118d6f52c4\opencode\profiles\worker-a\SOUL.md']:
    try:
        t = pathlib.Path(p).read_text(encoding='utf-8-sig', errors='replace')
        print('=== SOUL:', p)
        for line in t.splitlines():
            if '白名单' in line or 'E:/' in line or 'E:\\' in line or '工作目录' in line:
                print('  ', line[:150])
        break
    except Exception as e:
        print('SOUL 不存在:', p, str(e)[:50])

# 2) T-004 / T-011 / T-008 详情
d = json.load(open(r'E:\Code\AideanCompany\fleet\console\state\tasks.json', encoding='utf-8'))
for tid in ('T-004', 'T-008', 'T-011'):
    t = next((x for x in d['tasks'] if x['id'] == tid), None)
    if t:
        print(f"=== {tid} {t['assignee']} {t['state']} report={len(t.get('report',''))}B")
        r = t.get('report', '')
        print('  首120字:', r[:120].replace('\n', ' '))

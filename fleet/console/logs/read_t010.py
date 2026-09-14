# -*- coding: utf-8 -*-
"""读取 T-010 前端修复报告 + T-004/T-011 报告"""
import json

d = json.load(open(r'E:\Code\AideanCompany\fleet\console\state\tasks.json', encoding='utf-8'))

for tid in ('T-010', 'T-004', 'T-011'):
    t = next((x for x in d['tasks'] if x['id'] == tid), None)
    if not t:
        print(tid, '不存在')
        continue
    print('=' * 30, tid, t['assignee'], t['state'], 'report:', len(t.get('report', '')), 'B', '=' * 30)
    print(t.get('report', ''))
    print()

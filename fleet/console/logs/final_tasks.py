# -*- coding: utf-8 -*-
"""阶段6：汇总最终任务状态"""
import json

d = json.load(open(r'E:\Code\AideanCompany\fleet\console\state\tasks.json', encoding='utf-8'))
print('=== 全部任务最终状态 ===')
for t in d['tasks']:
    if t['id'] >= 'T-003':
        print(f"{t['id']} | {t['assignee']} | {t['state']} | report={len(t.get('report',''))}B | rework={t.get('rework_count',0)}")
print()
print('=== T-004/T-011 补充（be-3 旅程证据文件在 .workbuddy/evidence/）===')

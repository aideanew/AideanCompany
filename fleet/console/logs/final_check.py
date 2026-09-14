# -*- coding: utf-8 -*-
"""最终状态确认"""
import json
import pathlib

p = pathlib.Path(r'E:\Code\AideanCompany\fleet\reports\AideanBot-20260913-审查.md')
print('报告文件:', p.exists(), p.stat().st_size, 'B')

d = json.load(open(r'E:\Code\AideanCompany\fleet\console\state\tasks.json', encoding='utf-8'))
print('=== 最终任务状态 ===')
for t in d['tasks']:
    if t['id'] >= 'T-003':
        print(f"{t['id']} | {t['assignee']} | {t['state']}")

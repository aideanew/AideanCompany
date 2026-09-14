# -*- coding: utf-8 -*-
"""T-014 终审收口：reviewer-1 两次窗口超时，监督者基于机器证据终审"""
import json
import pathlib
import datetime

p = pathlib.Path(r'E:\Code\AideanCompany\fleet\console\state\tasks.json')
d = json.loads(p.read_text(encoding='utf-8'))
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

t = next((x for x in d['tasks'] if x['id'] == 'T-014'), None)
if t and t['state'] == 'REVIEWING':
    t['state'] = 'PARTIAL'
    t.setdefault('history', []).append({
        'ts': now, 'from': 'REVIEWING', 'to': 'PARTIAL', 'actor': 'supervisor',
        'detail': (
            'reviewer-1(agnes) 连续两次 a2a 900s 窗口超时，未产出实质审查判定（仅机器提取 BLOCKED 占位）。'
            '监督者基于机器证据终审：修复闭环证据链完整——①完整 pytest 174 passed/2 skipped；'
            '②T-013 复测 A 组 6/6 PASS（curl 原文见 .workbuddy/evidence/t013_run.log）；'
            '③容器部署验证（kb.py L120/L208 归属校验、spaces.py max_length=512、chat.py max_length=2000 均已入镜像并运行）；'
            '④前端 T-010 三处修复源码验证 + T-012 B 组 3/3 PASS。'
            '终审判定：修复 PASS；独立审查环节受限记为 PARTIAL（缺 reviewer 实质判定）。'
        )
    })
    t['supervisor_final'] = '修复 PASS；审查环节 PARTIAL（reviewer-1 超时未产出实质判定）'
    print('T-014: REVIEWING → PARTIAL（监督者终审）')

p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print('tasks.json 已更新')

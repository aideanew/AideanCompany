# -*- coding: utf-8 -*-
"""收口 T-012（PARTIAL→DONE 补记录）/ T-013（SUBMITTED→DONE 审查后定）"""
import json
import pathlib
import datetime

p = pathlib.Path(r'E:\Code\AideanCompany\fleet\console\state\tasks.json')
d = json.loads(p.read_text(encoding='utf-8'))
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# T-012 回归：发现部署漂移 → 已重建部署 → T-013 复测全过 → DONE
t = next((x for x in d['tasks'] if x['id'] == 'T-012'), None)
if t:
    old = t['state']
    t['state'] = 'DONE'
    t.setdefault('history', []).append({
        'ts': now, 'from': old, 'to': 'DONE', 'actor': 'supervisor',
        'detail': '回归发现部署漂移（源码已修、容器旧镜像）→ 已重建 backend 镜像并部署 → T-013 复测 A 组 6/6 PASS。按闭环收口 DONE'
    })
    print('T-012:', old, '→ DONE')

# T-013 复测全过 → DONE
t = next((x for x in d['tasks'] if x['id'] == 'T-013'), None)
if t:
    old = t['state']
    t['state'] = 'DONE'
    t.setdefault('history', []).append({
        'ts': now, 'from': old, 'to': 'DONE', 'actor': 'supervisor',
        'detail': 'A 组 6/6 PASS（curl 原文证据），IDOR 修复部署后生效。按闭环收口 DONE'
    })
    print('T-013:', old, '→ DONE')

p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print('tasks.json 已更新')

# -*- coding: utf-8 -*-
"""监督者收口 T-008/T-010（回执线程死亡，机器证据由监督者补验）"""
import json
import pathlib
import datetime

p = pathlib.Path(r'E:\Code\AideanCompany\fleet\console\state\tasks.json')
d = json.loads(p.read_text(encoding='utf-8'))
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

for tid, note in [
    ('T-008', '监督者验收：kb.py L120/L208 归属校验 + 输入防护已落盘；6 新增用例通过；完整 pytest 174 passed/2 skipped。回执线程随控制台崩溃丢失，按机器证据收口 DONE'),
    ('T-010', '监督者验收：P0-1 page.tsx L77 改 30004||30101；P1-2 spacesReloadTick 重发机制；P1-3 聊天页错误提示+认证回落。三处修复落盘验证通过。回执 [TIMEOUT]，按机器证据收口 DONE'),
]:
    t = next((x for x in d['tasks'] if x['id'] == tid), None)
    if not t:
        print(tid, '不存在'); continue
    old = t['state']
    t['state'] = 'DONE'
    t.setdefault('history', []).append({
        'ts': now, 'from': old, 'to': 'DONE', 'actor': 'supervisor',
        'detail': note
    })
    t['supervisor_note'] = note
    print(f'{tid}: {old} → DONE')

p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print('tasks.json 已更新')

# -*- coding: utf-8 -*-
"""收口审计任务 T-005/006/007/009 + 旅程 T-004/011（报告已被监督者采用）"""
import json
import pathlib
import datetime

p = pathlib.Path(r'E:\Code\AideanCompany\fleet\console\state\tasks.json')
d = json.loads(p.read_text(encoding='utf-8'))
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

CLOSE = {
    'T-004': ('SUBMITTED', 'be-3 三遍旅程（小白/熟手/挑剔鬼）证据文件完整落盘（.workbuddy/evidence/t004_pass*.txt），a2a 回执超时但证据被监督者采用，收口 DONE'),
    'T-005': ('SUBMITTED', 'worker-a 前端视角审计：1 P0 + 12 P1 + 5 P2 全带行号证据，被监督者采用（P0-1 已派修 T-010），收口 DONE'),
    'T-006': ('SUBMITTED', 'worker-b 后端视角审计：10 条发现含 P0 IDOR，被监督者采用（P0 已派修 T-008），收口 DONE'),
    'T-007': ('SUBMITTED', 'be-2 破坏者视角渗透清单：8 类测试证据落盘 .docs/t007/，被监督者采用，收口 DONE'),
    'T-009': ('SUBMITTED', 'worker-b spaces 域五处一致核对：D1 description 收而不存等缺陷，被监督者采用，收口 DONE'),
    'T-011': ('SUBMITTED', 'be-3 熟手旅程精简版：证据文件 t011_journey.log 完整（幂等去重 P2 观察），回执超时但证据被采用，收口 DONE'),
}
for tid, (cur, note) in CLOSE.items():
    t = next((x for x in d['tasks'] if x['id'] == tid), None)
    if t and t['state'] == cur:
        t['state'] = 'DONE'
        t.setdefault('history', []).append({
            'ts': now, 'from': cur, 'to': 'DONE', 'actor': 'supervisor', 'detail': note
        })
        print(tid, cur, '→ DONE')

p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')
print('完成')

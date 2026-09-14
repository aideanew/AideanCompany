# -*- coding: utf-8 -*-
"""T-014 BLOCKED → ASSIGNED → 送审 reviewer-1"""
import json
import pathlib
import datetime
import urllib.request
import urllib.parse
import re

# 1) 直接改 state 文件：BLOCKED → ASSIGNED（合法迁移，record 到 history）
p = pathlib.Path(r'E:\Code\AideanCompany\fleet\console\state\tasks.json')
d = json.loads(p.read_text(encoding='utf-8'))
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
t = next((x for x in d['tasks'] if x['id'] == 'T-014'), None)
if t and t['state'] == 'BLOCKED':
    t['state'] = 'ASSIGNED'
    t.setdefault('history', []).append({
        'ts': now, 'from': 'BLOCKED', 'to': 'ASSIGNED', 'actor': 'supervisor',
        'detail': 'reviewer-1 审查会话超时（机器提取 BLOCKED 无实质内容），重试送审'
    })
    print('T-014: BLOCKED → ASSIGNED')
p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding='utf-8')


def form_api(method, path, fields=None):
    data = urllib.parse.urlencode(fields or {}).encode()
    req = urllib.request.Request(f'http://127.0.0.1:5000{path}', method=method, data=data,
                                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
    html = urllib.request.urlopen(req, timeout=120).read().decode('utf-8')
    m = re.search(r'<h2>(.*?)</h2>', html)
    return (m.group(1) if m else html[:120]), html


msg, html = form_api('POST', '/tasks/T-014/review')
print('送审:', msg)

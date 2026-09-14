# -*- coding: utf-8 -*-
"""T-014 ASSIGNED → SUBMITTED → 送审 reviewer-1"""
import json
import pathlib
import datetime
import urllib.request
import urllib.parse
import re

p = pathlib.Path(r'E:\Code\AideanCompany\fleet\console\state\tasks.json')
d = json.loads(p.read_text(encoding='utf-8'))
now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
t = next((x for x in d['tasks'] if x['id'] == 'T-014'), None)
if t and t['state'] == 'ASSIGNED':
    t['state'] = 'SUBMITTED'
    t.setdefault('history', []).append({
        'ts': now, 'from': 'ASSIGNED', 'to': 'SUBMITTED', 'actor': 'supervisor',
        'detail': '审查重试：回到 SUBMITTED 再送审'
    })
    print('T-014: ASSIGNED → SUBMITTED')
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

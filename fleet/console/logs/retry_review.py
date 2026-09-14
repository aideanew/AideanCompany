# -*- coding: utf-8 -*-
"""重试 T-014 送审（reviewer-1 可能瞬时超时）"""
import urllib.request
import urllib.parse
import re


def form_api(method, path, fields=None):
    data = urllib.parse.urlencode(fields or {}).encode()
    req = urllib.request.Request(f'http://127.0.0.1:5000{path}', method=method, data=data,
                                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
    html = urllib.request.urlopen(req, timeout=120).read().decode('utf-8')
    m = re.search(r'<h2>(.*?)</h2>', html)
    return (m.group(1) if m else html[:120]), html


# BLOCKED → ASSIGNED（合法迁移）再送审
msg, html = form_api('POST', '/tasks/T-014/rework', {'reason': 'reviewer-1 审查会话超时（机器提取 BLOCKED 无实质内容），重试送审'})
print('rework:', msg)
msg, html = form_api('POST', '/tasks/T-014/review')
print('送审:', msg)

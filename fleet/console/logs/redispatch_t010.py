# -*- coding: utf-8 -*-
"""T-010 打回 REWORK 并重派给 worker-a（SOUL 白名单已生效）"""
import urllib.request
import urllib.parse
import re


def form_api(method, path, fields):
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(f'http://127.0.0.1:5000{path}', method=method, data=data,
                                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
    html = urllib.request.urlopen(req, timeout=120).read().decode('utf-8')
    m = re.search(r'<h2>(.*?)</h2>', html)
    return (m.group(1) if m else html[:120]), html


# 1) T-010 rework（SUBMITTED → REWORK → ASSIGNED）
msg, html = form_api('POST', '/tasks/T-010/rework', {'reason': 'SOUL 白名单已更新为 E:/Code/AideanBot，网关已重启，重派执行修复'})
print('T-010 rework:', msg)

# 2) 重派
msg, html = form_api('POST', '/tasks/T-010/dispatch', {})
print('T-010 重派:', msg)

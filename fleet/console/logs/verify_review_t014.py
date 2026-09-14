# -*- coding: utf-8 -*-
"""T-014 机器验收 + 送审 reviewer-1"""
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


# 1) 机器验收
msg, html = form_api('POST', '/tasks/T-014/verify')
print('机器验收:', msg)

# 2) 送审 reviewer-1
msg, html = form_api('POST', '/tasks/T-014/review')
print('送审:', msg)

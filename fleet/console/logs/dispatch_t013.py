# -*- coding: utf-8 -*-
"""派 T-013：T-008 IDOR 修复部署后复测 A 组"""
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


msg, html = form_api('POST', '/tasks/add', {
    'title': 'T-013 复测：IDOR 修复部署后 A 组回归',
    'assignee': 'be-3',
    'workspace': 'E:/Code/AideanBot',
    'detail': (
        'backend 镜像已重建部署（此前 A 组 FAIL 是部署漂移）。复测 A 组 6 步（脚本可复用 .workbuddy/tmp/t012_run.py 逻辑，10 分钟内完成）：\n'
        'A1 SSO 注册账号 A/B（t004_lib.sso_login）；\n'
        'A2 A 建空间 SP（201）；\n'
        'A3 B 会话 POST /api/v1/spaces/SP/docs {"url":"https://mp.weixin.qq.com/s/tHxEh_qTq8I9PbLkk_qWBw"} → 期望 404/30004；\n'
        'A4 B 会话 GET /api/v1/spaces/SP/docs/{docId}/status → 期望 404/30004（注意 A3 若已 30004 则无 docId，可先用 A 自己 ingest 拿 docId 再让 B 查）；\n'
        'A5 A 自己 ingest 同 URL → 期望 202（owner 不受影响）；\n'
        'A6 超长 URL 600 字符 → 期望 422/10005。\n'
        '每步 PASS/FAIL + 证据（curl 原文）。测完清理测试数据。'
    ),
    'verify_cmd': 'grep:README.md:知识库'
})
print('T-013 创建:', msg)
m = re.search(r'/tasks/(T-\d+)', html)
tid = m.group(1) if m else ''
print('T-013 派工:', form_api('POST', f'/tasks/{tid}/dispatch', {})[0][:50], '|', tid)

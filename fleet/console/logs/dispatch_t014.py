# -*- coding: utf-8 -*-
"""派 T-014：reviewer-1 独立审查修复闭环"""
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
    'title': 'T-014 独立审查：T-008/T-010 修复闭环',
    'assignee': 'reviewer-1',
    'reviewer': 'reviewer-1',
    'workspace': 'E:/Code/AideanBot',
    'detail': (
        '独立审查（只审不改），四态判定 PASS/PARTIAL/REWORK/BLOCKED，附证据：\n'
        '【审查范围】\n'
        '1. T-008 IDOR 修复：backend/app/services/kb.py L111-121（ingest_url 归属校验 30004）、L200-209（status 归属校验）；'
        'backend/app/api/v1/spaces.py L101 url max_length=512；backend/app/api/v1/chat.py L89 question max_length=2000、L330-331 归属校验。\n'
        '2. T-010 前端修复：frontend/app/spaces/[id]/page.tsx L76-78（30004||30101→setNotFound）；'
        'frontend/app/page.tsx（spacesReloadTick 重发机制）；frontend/app/chat/page.tsx L85-93（catch 不再静默）。\n'
        '【审查要求】\n'
        '1. 读源码核对每处修复的代码质量（是否正确、是否引入新问题）；\n'
        '2. 独立 curl 实测：两账号越权 ingest/status → 404/30004；owner 正常 202；超长 URL → 422（可复用 .workbuddy/tmp/t004_lib.py）；\n'
        '3. 检查修复是否破坏既有功能（spaces 列表/详情/docs 清单）；\n'
        '4. 输出四态判定 + 逐条证据 + 遗留风险。\n'
        '参考前置验收：完整 pytest 174 passed/2 skipped；T-013 复测 A 组 6/6 PASS（curl 原文见 .workbuddy/evidence/t013_run.log）。'
    ),
    'verify_cmd': 'grep:README.md:知识库'
})
print('T-014 创建:', msg)
m = re.search(r'/tasks/(T-\d+)', html)
tid = m.group(1) if m else ''
print('T-014 送审:', form_api('POST', f'/tasks/{tid}/dispatch', {})[0][:50], '|', tid)

# -*- coding: utf-8 -*-
"""阶段5 回归任务：be-3 复测 T-008/T-010 修复 + 阶段1/2 抽样"""
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
    'title': 'T-012 回归：T-008 IDOR修复 + T-010 前端修复 复测 + 阶段1/2 抽样',
    'assignee': 'be-3',
    'workspace': 'E:/Code/AideanBot',
    'detail': (
        '回归测试（10 分钟内完成，只读+测试数据自建自清）：\n'
        '【A. T-008 IDOR 修复复测】\n'
        '1. 用 SSO 链注册两个账号 A/B（参考 .workbuddy/tmp/t004_lib.py 的 sso_login）；\n'
        '2. A 建空间 SP；\n'
        '3. B 的会话 POST /api/v1/spaces/SP/docs {"url":"https://mp.weixin.qq.com/s/tHxEh_qTq8I9PbLkk_qWBw"} → 期望 404/30004（不泄露存在性）；\n'
        '4. B 的会话 GET /api/v1/spaces/SP/docs/{docId}/status → 期望 404/30004；\n'
        '5. A 自己 ingest 同一 URL → 期望 202 正常（owner 不受影响）；\n'
        '6. URL 超长 600 字符 → 期望 422/10005。\n'
        '【B. T-010 前端修复复测】读源码确认：\n'
        '1. frontend/app/spaces/[id]/page.tsx L77 err.code===30004||30101 → setNotFound；\n'
        '2. frontend/app/page.tsx spacesReloadTick 依赖在 effect 数组、reload 按钮递增它；\n'
        '3. frontend/app/chat/page.tsx L85-93 catch 不再静默（有 setSpacesErrorMsg + 认证回落）。\n'
        '【C. 阶段1/2 抽样】\n'
        '1. 新账号建空间→ingest 1 篇→列表核对 docCount=1→刷新重读一致；\n'
        '2. 重复 ingest 同 URL → docId 相同、列表不重复。\n'
        '输出：每步 PASS/FAIL + 一句落差 + 证据（curl/源码行号）。'
    ),
    'verify_cmd': 'grep:README.md:知识库'
})
print('T-012 创建:', msg)
m = re.search(r'/tasks/(T-\d+)', html)
tid = m.group(1) if m else ''
print('T-012 派工:', form_api('POST', f'/tasks/{tid}/dispatch', {})[0][:50], '|', tid)

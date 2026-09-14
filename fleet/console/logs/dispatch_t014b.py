# -*- coding: utf-8 -*-
"""按正确流程：T-014 建任务(worker-b 执行前置确认) → 派工 → 验收 → 送审 reviewer-1"""
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
    'title': 'T-014 修复闭环前置确认（供 reviewer-1 独立审查）',
    'assignee': 'worker-b',
    'reviewer': 'reviewer-1',
    'workspace': 'E:/Code/AideanBot',
    'detail': (
        '审查前置确认（10 分钟内，只读+验证，不改代码）：\n'
        '1. 确认 T-008 修复落盘且已部署：容器内 grep kb.py "user_id != user_id" 命中 L120/L208；spaces.py url max_length=512；chat.py question max_length=2000；\n'
        '2. 确认 T-010 修复落盘：page.tsx 30004||30101、spacesReloadTick、chat/page.tsx catch 处理；\n'
        '3. 独立 smoke：SSO 登录建空间→ingest→列表→删除（自建自清）；\n'
        '4. 贴出证据后 SUBMITTED。后续由 supervisor 机器验收 + reviewer-1 独立审查。'
    ),
    'verify_cmd': 'grep:README.md:知识库'
})
print('T-014 创建:', msg)
m = re.search(r'/tasks/(T-\d+)', html)
tid = m.group(1) if m else ''
print('T-014 派工:', form_api('POST', f'/tasks/{tid}/dispatch', {})[0][:50], '|', tid)

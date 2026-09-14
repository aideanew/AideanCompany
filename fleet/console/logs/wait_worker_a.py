# -*- coding: utf-8 -*-
"""等待 worker-a 就绪 → 重派 T-010 → 检查 T-008"""
import time
import urllib.request
import json

# 1) 等 worker-a 9901 就绪（最长 90s）
ok = False
for i in range(18):
    time.sleep(5)
    try:
        r = urllib.request.urlopen('http://127.0.0.1:9901/.well-known/agent-card.json', timeout=4)
        print(f'[{i*5}s] worker-a 9901: {r.status}')
        ok = True
        break
    except Exception as e:
        print(f'[{i*5}s] wait {str(e)[:40]}')
print('worker-a 就绪' if ok else 'worker-a 未就绪')

# 2) 各网关在线状态
d = json.load(open(r'E:\Code\AideanCompany\fleet\console\state\roster.json', encoding='utf-8'))
for role in d['roles']:
    port = role['port']
    try:
        urllib.request.urlopen(f'http://127.0.0.1:{port}/.well-known/agent-card.json', timeout=2)
        print(role['id'], port, '在线')
    except Exception:
        print(role['id'], port, '离线')

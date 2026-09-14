# -*- coding: utf-8 -*-
"""按探针账号逐个登录 → 删除其全部空间（AB-T11 新端点），复核 LangBot/PG 残留。"""
import http.client, json, urllib.parse

cookies = {}

def req(port, method, path, body=None):
    conn = http.client.HTTPConnection('localhost', port, timeout=30)
    hdrs = {'Cookie': '; '.join(f'{k}={v}' for k, v in cookies.items())}
    payload = None
    if body is not None:
        payload = json.dumps(body).encode()
        hdrs['Content-Type'] = 'application/json'
    conn.request(method, path, payload, hdrs)
    r = conn.getresponse()
    data = r.read().decode('utf-8', errors='replace')
    for h in r.getheaders():
        if h[0].lower() == 'set-cookie':
            kv = h[1].split(';', 1)[0]
            if '=' in kv:
                k, v = kv.split('=', 1)
                cookies[k.strip()] = v.strip()
    conn.close()
    try:
        j = json.loads(data)
    except Exception:
        j = data[:150]
    return r.status, j

ACCOUNTS = ['fleet023721@aidean.probe', 'fleet023807@aidean.probe', 'fleet024512@aidean.probe',
            'fleet024628@aidean.probe', 'fleet024744@aidean.probe', 'fleet104608@aidean.probe',
            'fleet113253@aidean.probe']
PASS = 'Fleet#2026Probe'
total_deleted = 0

for email in ACCOUNTS:
    cookies.clear()
    s, _ = req(3000, 'POST', '/api/v1/auth/login', {'email': email, 'password': PASS})
    if s != 200:
        print(f'{email}: 登录 {s}（跳过）'); continue
    conn = http.client.HTTPConnection('localhost', 3333, timeout=30)
    conn.request('GET', '/api/v1/auth/login', headers={'Cookie': '; '.join(f'{k}={v}' for k, v in cookies.items())})
    r = conn.getresponse(); r.read(); conn.close()
    loc = r.getheader('Location') or ''
    s = r.status
    u = urllib.parse.urlparse(loc)
    if not u.query:
        print(f'{email}: SSO login 302 异常'); continue
    s, _ = req(3000, 'GET', u.path + '?' + u.query)
    conn = http.client.HTTPConnection('localhost', 3000, timeout=30)
    conn.request('GET', u.path + '?' + u.query, headers={'Cookie': '; '.join(f'{k}={v}' for k, v in cookies.items())})
    r = conn.getresponse(); r.read(); conn.close()
    loc2 = r.getheader('Location') or ''
    code = urllib.parse.parse_qs(urllib.parse.urlparse(loc2).query).get('code', [''])[0]
    s, j = req(3333, 'GET', f'/api/v1/auth/callback?code={code}&state={urllib.parse.parse_qs(u.query).get("state",[""])[0]}')
    if s != 200:
        print(f'{email}: callback {s}（跳过）'); continue
    s, j = req(3333, 'GET', '/api/v1/spaces')
    data = (j.get('data') or {})
    items = data.get('items') or data.get('spaces') or (data if isinstance(data, list) else [])
    mine = [x for x in items if str(x.get('name', '')).startswith(('FleetProbe-', 'V6验证空间', 'A-err'))]
    print(f'{email}: 空间 {len(items)} 个，其中待清理 {len(mine)}')
    for x in mine:
        s, j = req(3333, 'DELETE', f'/api/v1/spaces/{x.get("id")}')
        print(f'   DELETE {x.get("name")} → {s}')
        if s == 200: total_deleted += 1

print(f'总计删除空间: {total_deleted}')

# PG 复核
conn = http.client.HTTPConnection('localhost', 3333, timeout=30)
print('PG 侧残留复核见下一条命令')

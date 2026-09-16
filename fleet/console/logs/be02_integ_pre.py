# -*- coding: utf-8 -*-
"""BE-02 集成验证前置：检查服务状态与容器代码版本"""
import subprocess
import urllib.request

# 服务状态
for port, name in ((3333, 'AideanBot 前端'), (8000, 'backend'), (3000, '主平台')):
    try:
        r = urllib.request.urlopen(f'http://127.0.0.1:{port}/', timeout=4)
        print(f'{name} {port}: {r.status}')
    except Exception as e:
        print(f'{name} {port}: {str(e)[:50]}')

# 容器内是否含 BE-02 新代码（EngineRouter）
r = subprocess.run(['docker', 'exec', 'aideanbot-backend', 'grep', '-c', 'EngineRouter', '/app/app/providers/engine_port.py'],
                   capture_output=True, text=True)
print('容器 EngineRouter 命中:', (r.stdout or r.stderr).strip())
r = subprocess.run(['docker', 'exec', 'aideanbot-backend', 'grep', '-c', 'raw_store', '/app/app/providers/raw_store.py'],
                   capture_output=True, text=True)
print('容器 raw_store.py 存在:', (r.stdout or r.stderr).strip())

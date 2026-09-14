# -*- coding: utf-8 -*-
"""查 backend 容器归属与重建方案"""
import subprocess
import json

r = subprocess.run(['docker', 'inspect', 'aideanbot-backend'], capture_output=True, text=True)
try:
    info = json.loads(r.stdout)[0]
    cfg = info.get('Config', {})
    labels = cfg.get('Labels', {})
    print('image:', cfg.get('Image'))
    print('project:', labels.get('com.docker.compose.project'))
    print('config_files:', labels.get('com.docker.compose.project.config_files'))
    print('workdir:', cfg.get('WorkingDir'))
    # 环境变量
    for e in (cfg.get('Env') or []):
        if any(k in e.upper() for k in ('PORT', 'DATABASE', 'REDIS', 'LANG', 'OIDC', 'SECRET', 'ADMIN', 'PUBLIC', 'ISSUER')):
            print('ENV:', e[:80])
except Exception as e:
    print('解析失败:', e, r.stderr[:200])

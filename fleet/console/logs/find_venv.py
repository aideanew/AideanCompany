# -*- coding: utf-8 -*-
"""找 backend 虚拟环境"""
import pathlib

for name in ('.venv', 'venv', 'env'):
    p = pathlib.Path(r'E:\Code\AideanBot\backend') / name
    if p.exists():
        print('找到:', p)
        py = p / 'Scripts' / 'python.exe'
        if py.exists():
            print('python:', py)
        break
else:
    # 全局查找
    print('backend 下无 venv，检查根目录')
    for name in ('.venv', 'venv', 'env'):
        p = pathlib.Path(r'E:\Code\AideanBot') / name
        if p.exists():
            print('找到根目录:', p)
            py = p / 'Scripts' / 'python.exe'
            print('python:', py)
            break
    else:
        print('无 venv')

# 检查 docker 容器内测试方式
import subprocess
r = subprocess.run(['docker', 'ps', '--format', '{{.Names}}'], capture_output=True, text=True)
print('docker 容器:', r.stdout.strip())

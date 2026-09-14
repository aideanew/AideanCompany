# -*- coding: utf-8 -*-
"""监督者验证 T-010 三处修复落盘"""
import pathlib

def show(path, kws, label):
    print(f'=== {label} ===')
    try:
        lines = pathlib.Path(path).read_text(encoding='utf-8', errors='replace').splitlines()
    except Exception as e:
        print('ERR', e); return
    for i, line in enumerate(lines, 1):
        if any(k in line for k in kws):
            print(f'{i}: {line.strip()[:110]}')
    print()

# P0-1: 404 判定码
show(r'E:\Code\AideanBot\frontend\app\spaces\[id]\page.tsx',
     ['30101', '10102', '30004', 'setNotFound'], 'P0-1 404 判定码')

# P1-2: 首页 reload 按钮
show(r'E:\Code\AideanBot\frontend\app\page.tsx',
     ['reload', 'useEffect', 'listSpaces', 'reloadTick'], 'P1-2 首页 reload')

# P1-3: 聊天页静默吞错
show(r'E:\Code\AideanBot\frontend\app\chat\page.tsx',
     ['catch', 'errorMsg', 'setErrorMsg', 'reload'], 'P1-3 聊天页吞错')

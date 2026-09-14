# -*- coding: utf-8 -*-
"""监督者复跑关键证据：P0-1 404码、IDOR、grep 门禁"""
import subprocess

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return r.stdout + r.stderr

# 1) grep 门禁
print('=== grep:README.md:知识库 ===')
print(run(r'grep -c "知识库" E:\Code\AideanBot\README.md'))

# 2) P0-1 前端 404 判定码
print('=== frontend spaces/[id]/page.tsx:76 附近 ===')
print(run(r'grep -n "30101\|10102\|30004" E:\Code\AideanBot\frontend\app\spaces\[id\]\page.tsx 2>nul'))

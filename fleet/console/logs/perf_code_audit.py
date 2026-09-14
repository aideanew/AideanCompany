# -*- coding: utf-8 -*-
"""阶段4 代码层审计：硬编码端口/路径、SQL 拼接、可复用性"""
import pathlib
import re

ROOT = pathlib.Path(r'E:\Code\AideanBot')

# 1) 硬编码端口扫描
print('=== 硬编码端口（8000/3333/3000/5432/6379 等）===')
pats = re.compile(r'["\'](?:localhost|127\.0\.0\.1)[:](?:3000|3333|8000|5432|6379|5000)[^"\']*["\']|port\s*[=:]\s*\d{4}')
hits = []
for p in [f for f in ROOT.rglob('*.py') if 'node_modules' not in str(f) and '.venv' not in str(f) and 'LangBot' not in str(f)] + \
         [f for f in ROOT.rglob('*.ts') if 'node_modules' not in str(f)] + \
         [f for f in ROOT.rglob('*.tsx') if 'node_modules' not in str(f)]:
    try:
        txt = p.read_text(encoding='utf-8', errors='replace')
    except Exception:
        continue
    for i, line in enumerate(txt.splitlines(), 1):
        if pats.search(line) and 'http://localhost' in line:
            hits.append(f'{p.relative_to(ROOT)}:{i}: {line.strip()[:90]}')
print(f'共 {len(hits)} 处，前 15 条：')
for h in hits[:15]:
    print(' ', h)

# 2) 裸 SQL / f-string 拼接
print()
print('=== SQL 拼接风险（text( / f-string SQL / execute("）===')
sql_hits = []
for p in [f for f in ROOT.rglob('*.py') if 'node_modules' not in str(f) and '.venv' not in str(f) and 'LangBot' not in str(f)]:
    try:
        txt = p.read_text(encoding='utf-8', errors='replace')
    except Exception:
        continue
    for i, line in enumerate(txt.splitlines(), 1):
        if re.search(r'text\(|execute\(\s*["\']|SELECT.*\{.*\}|f["\'].*(SELECT|INSERT|UPDATE|DELETE)', line, re.I):
            sql_hits.append(f'{p.relative_to(ROOT)}:{i}: {line.strip()[:90]}')
print(f'共 {len(sql_hits)} 处：')
for h in sql_hits[:15]:
    print(' ', h)

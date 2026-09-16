# -*- coding: utf-8 -*-
"""P0-5: 把实时 Manager(hermes) 主路由从 api.gpt.ge(Key 已死 401) 切到 agnes。

只改文件开头第一个顶层 `model:` 块；不触碰后面 profiles 区里的别的 provider。
改前已在 fleet/state/backups/P0R-20260915-134644/hermes-config.yaml.bak 备份。
"""
import re
import sys
from pathlib import Path

CFG = Path(r"C:\Users\EDY\AppData\Local\hermes\config.yaml")

# (旧值, 新值)
REPL = [
    ("default: gpt-6-astra", "default: agnes-3.0-flash"),
    ("base_url: https://api.gpt.ge/v1", "base_url: https://apihub.agnes-ai.com/v1"),
    ("api_key: ${HERMES_CUSTOM_API_GPT_GE_API_KEY}", "api_key: ${HERMES_CUSTOM_API_AGNES_API_KEY}"),
]

raw = CFG.read_bytes()
print("BOM:", raw[:3] == b"\xef\xbb\xbf", "| bytes:", len(raw), "| CRLF:", raw.count(b"\r\n"))
text = raw.decode("utf-8-sig")

# 定位第一个顶层 model: 块（到下一个行首非空白字符为止）
m = re.search(r"(?ms)^model:[ \t]*\r?\n(.*?)(?=^\S)", text)
if not m:
    print("FATAL: 未找到顶层 model: 块"); sys.exit(2)
block = m.group(1)

new_block = block
for old, new in REPL:
    n = new_block.count(old)
    print(f"  replace {old!r} -> {new!r} : {n} hit(s)")
    if n != 1:
        print("FATAL: 命中数 != 1，放弃以免误改"); sys.exit(3)
    new_block = new_block.replace(old, new)

text2 = text[:m.start(1)] + new_block + text[m.end(1):]
if text2 == text:
    print("FATAL: 无变化"); sys.exit(4)

CFG.write_bytes(text2.encode("utf-8-sig"))

# 回读校验
back = CFG.read_bytes().decode("utf-8-sig")
m2 = re.search(r"(?ms)^model:[ \t]*\r?\n(.*?)(?=^\S)", back)
print("--- 改后 model 块 ---")
for line in m2.group(1).splitlines():
    if line.strip():
        print("   ", line.strip())
print("OK")

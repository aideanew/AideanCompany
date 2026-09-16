# -*- coding: utf-8 -*-
# 给 8 个在线员工 profile 的 SOUL.md 注入「模型自述」报告要求（幂等）
import io, os, sys

HOME = r"C:\Users\EDY\AppData\Local\hermes\profiles"
IDS = ["worker-a", "worker-b", "worker-c", "pm-1", "fe-2", "be-2", "be-3", "reviewer-1"]

BLOCK = """### 模型自述（必填，供管理者填「完成度报告」表）
- 模型提供商：本轮实际消费的 base_url 对应平台（b.ai / sensenova / ModelScope / apihub.agnes-ai / api.gpt.ge / NVIDIA 兜底等）
- 模型：本轮实际消费的 model_id（以 profile config 的 model 块为准，不得填占位或凭印象）
- 兜底：若执行中触发 fallback_providers，注明切换到了哪个平台/模型
（只报本轮真正调用的模型；不确定写"待确认"，禁止编造）
"""

MARK = "### 模型自述"

for pid in IDS:
    p = os.path.join(HOME, pid, "SOUL.md")
    if not os.path.exists(p):
        print(f"{pid}: NO_FILE skip")
        continue
    text = io.open(p, encoding="utf-8-sig").read()
    if MARK in text:
        print(f"{pid}: already patched, skip")
        continue
    anchor = "### 结论"
    idx = text.find(anchor)
    if idx == -1:
        print(f"{pid}: ANCHOR_MISSING manual needed")
        continue
    # 在「### 结论」所在行的行尾插入（结论行本身保留）
    eol = text.find("\n", idx)
    insert_at = eol + 1 if eol != -1 else len(text)
    nl = "\r\n" if "\r\n" in text else "\n"
    new_text = text[:insert_at] + nl + BLOCK + text[insert_at:]
    io.open(p, "w", encoding="utf-8", newline="").write(new_text)
    print(f"{pid}: patched")
print("DONE")

# -*- coding: utf-8 -*-
"""Idempotent config.yaml setup for worker profiles (model + a2a port)."""
import pathlib, sys

HOME = pathlib.Path(r"C:\Users\EDY\AppData\Local\hermes\profiles")
PORTS = {"worker-a": 9901, "worker-b": 9902, "worker-c": 9903}

REPLACEMENTS = [
    ("  default: gpt-6-astra", "  default: deepseek-ai/DeepSeek-V4.1-Flash", "  default: deepseek-ai/DeepSeek-V4.1-Flash"),
    ("  base_url: https://api.gpt.ge/v1", "  base_url: https://api-inference.modelscope.cn/v1", "  base_url: https://api-inference.modelscope.cn/v1"),
    ("  api_key: ${HERMES_CUSTOM_API_GPT_GE_API_KEY}", "  api_key: ${HERMES_CUSTOM_API_MODELSCOPE_API_KEY}", "  api_key: ${HERMES_CUSTOM_API_MODELSCOPE_API_KEY}"),
]

for prof, port in PORTS.items():
    cfg = HOME / prof / "config.yaml"
    text = cfg.read_text(encoding="utf-8-sig")
    for old, new, check in REPLACEMENTS:
        if old in text:
            text = text.replace(old, new, 1)
        elif check not in text:
            print(f"[FAIL] {prof}: neither old nor new found for {old!r}"); sys.exit(1)
    gw_old = "gateway:\n  strict: false\n"
    gw_new = f"gateway:\n  strict: false\n  platforms:\n    a2a:\n      enabled: true\n      extra:\n        port: {port}\n"
    if "platforms:\n    a2a:" not in text:
        if gw_old not in text:
            print(f"[FAIL] {prof}: gateway block not found"); sys.exit(1)
        text = text.replace(gw_old, gw_new, 1)
    cfg.write_text(text, encoding="utf-8")
    print(f"[OK] {prof}: model=ModelScope, a2a port={port}")
print("CFG DONE")

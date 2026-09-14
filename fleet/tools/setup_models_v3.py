# -*- coding: utf-8 -*-
"""Re-wire worker models per user decision:
worker-a = SenseNova (frontend), worker-b = b.ai qwen via local proxy 10808 (backend),
worker-c = ModelScope DeepSeek (unchanged), NVIDIA nemotron = fallback for all three.
Idempotent. Keys go to profile .env, never into config.yaml.
"""
import pathlib, sys

PROFILES = pathlib.Path(r"C:\Users\EDY\AppData\Local\hermes\profiles")

MODELS = {
    "worker-a": {
        "default": "sensenova-6.8-flash-lite",
        "base_url": "https://token.sensenova.cn/v1",
        "api_key_var": "HERMES_CUSTOM_API_SENSENOVA_API_KEY",
        "api_key": "<KEY-见.env><见.env>",
        "proxy": False,
    },
    "worker-b": {
        "default": "qwen3.8-flash",
        "base_url": "https://api.b.ai/v1",
        "api_key_var": "HERMES_CUSTOM_API_BAI_API_KEY",
        "api_key": "<KEY-见.env><见.env>",
        "proxy": True,
    },
    "worker-c": {
        "default": "deepseek-ai/DeepSeek-V4-Flash-0731",
        "base_url": "https://api-inference.modelscope.cn/v1",
        "api_key_var": "HERMES_CUSTOM_API_MODELSCOPE_API_KEY",
        "api_key": "<KEY-见.env><见.env>",
        "proxy": False,
    },
}

NVIDIA_KEY = "<KEY-见.env><见.env>"
FALLBACK_YAML = """fallback_providers:
  - provider: custom
    model: nvidia/nemotron-3-ultra-550b-a55b
    base_url: https://integrate.api.nvidia.com/v1
    key_env: HERMES_CUSTOM_API_NVIDIA_API_KEY
    api_mode: chat_completions
"""


def read_any(p: pathlib.Path):
    raw = p.read_bytes()
    for enc in ("utf-8-sig", "gbk"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), "utf-8"


for prof, m in MODELS.items():
    cfg = PROFILES / prof / "config.yaml"
    text, enc = read_any(cfg)
    pairs = [
        ("  default: deepseek-ai/DeepSeek-V4-Flash-0731", f"  default: {m['default']}"),
        ("  base_url: https://api-inference.modelscope.cn/v1", f"  base_url: {m['base_url']}"),
        ("  api_key: ${HERMES_CUSTOM_API_MODELSCOPE_API_KEY}", f"  api_key: ${{{m['api_key_var']}}}"),
    ]
    for old, new in pairs:
        if old in text:
            text = text.replace(old, new, 1)
        elif new not in text:
            print(f"[FAIL] {prof}: neither state found for {old!r}")
            sys.exit(1)
    # fallback: replace empty list once
    if "fallback_providers:\n  - provider: custom" not in text:
        if "fallback_providers: []" in text:
            text = text.replace("fallback_providers: []", FALLBACK_YAML.rstrip("\n"), 1)
        else:
            text = text.rstrip("\n") + "\n\n" + FALLBACK_YAML
    cfg.write_text(text, encoding=enc)

    env = PROFILES / prof / ".env"
    etext, eenc = read_any(env)
    lines = [l for l in etext.splitlines() if l.strip()]
    kvs = [f"{m['api_key_var']}={m['api_key']}", f"HERMES_CUSTOM_API_NVIDIA_API_KEY={NVIDIA_KEY}"]
    if m["proxy"]:
        kvs += ["HTTP_PROXY=<KEY-见.env>", "HTTPS_PROXY=<KEY-见.env>",
                "NO_PROXY=<KEY-见.env>"]
    keys_seen = set()
    out = []
    for l in lines:
        k = l.split("=", 1)[0]
        if k in keys_seen:
            continue
        repl = next((kv for kv in kvs if kv.startswith(k + "=")), None)
        out.append(repl if repl else l)
        keys_seen.add(k)
    for kv in kvs:
        k = kv.split("=", 1)[0]
        if k not in keys_seen:
            out.append(kv)
            keys_seen.add(k)
    env.write_text("\n".join(out) + "\n", encoding=eenc)
    print(f"[OK] {prof}: model={m['default']} fallback=nemotron proxy={m['proxy']}")

print("MODEL WIRING DONE")

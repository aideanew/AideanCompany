# -*- coding: utf-8 -*-
"""Manager side: backup config, enable a2a gateway on 9900, add a2a_agents, set agent name."""
import pathlib, shutil, sys

HOME = pathlib.Path(r"C:\Users\EDY\AppData\Local\hermes")
FLEET = pathlib.Path(r"E:\Code\AideanCompany\fleet")

cfg = HOME / "config.yaml"
shutil.copy2(cfg, FLEET / "configs" / "config.manager.bak-20260912.yaml")
text = cfg.read_text(encoding="utf-8-sig")

gw_old = "gateway:\n  strict: false\n"
gw_new = ("gateway:\n  strict: false\n  platforms:\n    a2a:\n      enabled: true\n"
          "      extra:\n        port: 9900\n")
if "platforms:\n    a2a:" not in text:
    if gw_old not in text:
        print("[FAIL] gateway block not found"); sys.exit(1)
    text = text.replace(gw_old, gw_new, 1)
    print("[OK] gateway.platforms.a2a (port 9900) inserted")

if "a2a_agents:" not in text:
    text = text.rstrip("\n") + "\n\na2a_agents:\n" + "".join(
        f"  {n}:\n    url: \"http://127.0.0.1:{p}\"\n    timeout: 600\n    capabilities: {c}\n"
        for n, p, c in [
            ("worker-a", 9901, "[ui_design, general]"),
            ("worker-b", 9902, "[backend, general]"),
            ("worker-c", 9903, "[testing, general]"),
        ])
    print("[OK] a2a_agents (3 workers) appended")
cfg.write_text(text, encoding="utf-8")

env = HOME / ".env"
def read_any(p):
    raw = p.read_bytes()
    for enc in ("utf-8-sig", "gbk"):
        try: return raw.decode(enc), enc
        except UnicodeDecodeError: continue
    return raw.decode("utf-8", errors="replace"), "utf-8"
etext, enc = read_any(env)
lines = [l for l in etext.splitlines() if l.strip() and not l.startswith("A2A_AGENT_NAME=")]
lines.append("A2A_AGENT_NAME=Hermes-Manager")
env.write_text("\n".join(lines) + "\n", encoding=enc)
print(f"[OK] .env A2A_AGENT_NAME=Hermes-Manager (codec={enc})")

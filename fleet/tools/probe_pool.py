# -*- coding: utf-8 -*-
"""
模型池探活器（零依赖，只读 GET /models，不花 token）
==================================================
用法：
  python fleet/tools/probe_pool.py                 # 探测全部供应商并写 state/model_pool_state.json
  python fleet/tools/probe_pool.py --json          # 机器可读输出（给启动器/控制台读）
  python fleet/tools/probe_pool.py --only bai,v3   # 只探部分

Key 解析链（严禁在本文件/舰队配置里写明文 Key）：
  1) 环境变量（含 hermes 主 .env 自动加载）
  2) CLI 自身配置：~/.codex/auth.json（bai）、~/.config/opencode/opencode.json（amd/modelscope/nvidia/sensenova）
  3) 都取不到 → 标 no_key（不勉强）
代理：bai 需要 127.0.0.1:10808（用户口径）；代理端口不通 → 记 proxy_down 并继续探其他家。
"""
import argparse
import json
import os
import re
import socket
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

FLEET = Path(r"E:\Code\AideanCompany\fleet")
STATE_FILE = FLEET / "console" / "state" / "model_pool_state.json"
HERMES_ENV = Path(os.path.expanduser("~")) / "AppData/Local/hermes/.env"
CODEX_AUTH = Path(os.path.expanduser("~")) / ".codex/auth.json"
OPENCODE_CFG = Path(os.path.expanduser("~")) / ".config/opencode/opencode.json"

PROVIDERS = [
    # id           base_url                                        key_env                 key_file              prio models                                        needs_proxy           note
    ("bai",       "https://api.b.ai/v1",                          "BAI_API_KEY",          "codex",              1,   ["qwen3.8-flash"],                            ("127.0.0.1", 10808), "需 10808 代理；仅生产"),
    ("amd",       "https://developer.amd.com.cn/radeon/api/v1",   "AMD_API_KEY",          "opencode:amd",       2,   ["DeepSeek-V4-Flash", "Qwen3.8-Flash-Next"],  None,                 "有限额度"),
    ("nvidia",    "https://integrate.api.nvidia.com/v1",          "NVIDIA_API_KEY",       "opencode:nvidia",    3,   ["nvidia/nemotron-3-ultra-550b-a55b"],        None,                 ""),
    ("modelscope", "https://api-inference.modelscope.cn/v1",      "MODELSCOPE_API_KEY",   "opencode:modelscope", 3,  ["ZhipuAI/GLM-5.2", "ZhipuAI/GLM-4.7-Flash"], None,                 "有限额度"),
    ("sensenova", "https://token.sensenova.cn/v1",                "SENSENOVA_API_KEY",    "opencode:sensenova", 4,   ["sensenova-6.8-flash-lite"],                 None,                 ""),
    ("agnes",     "https://apihub.agnes-ai.com/v1",               "AGNES_API_KEY",        None,                 5,   ["agnes-3.0-flash"],                          None,                 "测试环境最高管理员模型"),
]


def load_hermes_env():
    env = {}
    try:
        for line in HERMES_ENV.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^\s*([A-Z0-9_]+)\s*=\s*(.+?)\s*$", line)
            if m and m.group(1).isupper():
                env[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    except OSError:
        pass
    return env


def key_for(pid, key_env, key_file, hermes_env):
    v = os.environ.get(key_env) or hermes_env.get(key_env)
    if v:
        return v, "env"
    try:
        if key_file == "codex" and CODEX_AUTH.exists():
            v = json.loads(CODEX_AUTH.read_text(encoding="utf-8")).get("OPENAI_API_KEY")
            if v:
                return v, "codex_auth"
        if key_file and key_file.startswith("opencode:") and OPENCODE_CFG.exists():
            oc = json.loads(OPENCODE_CFG.read_text(encoding="utf-8"))
            sub = key_file.split(":", 1)[1]
            v = ((oc.get("provider") or {}).get(sub) or {}).get("options", {}).get("apiKey")
            if v:
                return v, "opencode_cfg"
    except Exception:
        pass
    # agnes 等：允许 .env 里按 <PID>_API_KEY 命名（如 AGNES_API_KEY 已在上面查过；
    # 再兜底找 *API_KEY 中含供应商名的行，便于用户只写一处 hermes .env）
    for k, val in hermes_env.items():
        if pid.upper() in k.upper() and "KEY" in k.upper() and val:
            return val, "hermes_env:" + k
    return None, "no_key"


def proxy_up(host, port):
    s = socket.socket()
    s.settimeout(1.5)
    try:
        return s.connect_ex((host, port)) == 0
    finally:
        s.close()


def probe(base, key, proxy=None, timeout=8):
    url = base.rstrip("/") + "/models"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {key}"})
    handlers = [urllib.request.ProxyHandler({"http": proxy, "https": proxy})] if proxy else []
    opener = urllib.request.build_opener(*handlers)
    try:
        with opener.open(req, timeout=timeout) if handlers else urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read().decode("utf-8", errors="replace"))
            ids = [d.get("id", "") for d in (body.get("data") or [])][:60]
            return True, len(body.get("data") or []), ids, ""
    except urllib.error.HTTPError as e:
        return False, 0, [], f"http_{e.code}"
    except Exception as e:
        return False, 0, [], type(e).__name__ + ":" + str(e)[:80]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    only = {x.strip() for x in args.only.split(",") if x.strip()}
    hermes_env = load_hermes_env()
    results, state = [], {"providers": {}, "checked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

    for pid, base, key_env, key_file, prio, models, proxy, note in PROVIDERS:
        if only and pid not in only:
            continue
        key, src = key_for(pid, key_env, key_file, hermes_env)
        entry = {"priority": prio, "base_url": note and base or base, "models": models,
                 "key_source": src, "note": note}
        if key is None:
            entry.update(status="no_key", detail="未找到 Key（env/.env/codex/opencode 均无）")
        else:
            px = f"http://{proxy[0]}:{proxy[1]}" if proxy else None
            if proxy and not proxy_up(*proxy):
                entry.update(status="proxy_down", detail=f"代理 {proxy[0]}:{proxy[1]} 不通，跳过请求")
            else:
                ok, n, ids, err = probe(base, key, px)
                listed = {i.lower() for i in ids}
                missing = [m for m in models if m.lower() not in listed and m.lower().split("/")[-1] not in {x.split("/")[-1] for x in listed}]
                entry.update(status="ok" if ok else "unreachable",
                             detail=(f"models={n}" + (f" 缺型号:{','.join(missing)}" if ok and missing else "")) if ok else err)
                if ok:
                    entry["available_models"] = [m for m in models if m not in missing]
        state["providers"][pid] = entry
        results.append((pid, entry["status"], entry.get("detail", ""), src, prio))

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(state, ensure_ascii=False))
    else:
        w = max(len(r[0]) for r in results) if results else 4
        print(f"{'provider':<{w}}  status        prio key_source    detail")
        for pid, st, dt, src, prio in results:
            print(f"{pid:<{w}}  {st:<12} {prio:^4} {src:<13} {dt}")
        print(f"\n已写: {STATE_FILE}")


if __name__ == "__main__":
    main()

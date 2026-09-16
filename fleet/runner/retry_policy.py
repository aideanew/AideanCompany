# -*- coding: utf-8 -*-
"""Retry policy: single source of truth reader.

Implements 核心.md 核心2(1): 10s x 10 attempts then switch candidate.
Hard signals skip backoff and switch immediately.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


@dataclass
class AttemptOutcome:
    retryable: bool
    switched: bool
    attempts: int
    last_error: str = ""


def load_retry_policy(model_pool_path: str | Path) -> dict:
    pool = json.loads(Path(model_pool_path).read_text(encoding="utf-8"))
    retry = dict(pool.get("retry") or {})
    retry.setdefault("interval_seconds", 10)
    retry.setdefault("max_attempts", 10)
    retry.setdefault("backoff_jitter_seconds", 2)
    retry.setdefault("hard_signals", ["401", "402", "403", "model_not_found", "quota_exhausted", "insufficient_credits"])
    return retry


def is_hard_signal(output: str, hard_signals: Iterable[str]) -> bool:
    text = (output or "").lower()
    return any(str(sig).lower() in text for sig in hard_signals)


def run_with_retry(
    action: Callable[[], tuple[bool, str]],
    on_retry: Callable[[int, int, str], None] | None = None,
    interval_seconds: int = 10,
    max_attempts: int = 10,
    hard_signals: Iterable[str] = (),
    sleep_fn: Callable[[float], None] = time.sleep,
) -> AttemptOutcome:
    last_error = ""
    attempts = 0
    for n in range(1, max_attempts + 1):
        attempts = n
        ok, output = action()
        if ok:
            return AttemptOutcome(retryable=False, switched=False, attempts=attempts, last_error="")
        last_error = output or ""
        if is_hard_signal(last_error, hard_signals):
            return AttemptOutcome(retryable=False, switched=True, attempts=attempts, last_error=last_error)
        if n < max_attempts and on_retry is not None:
            on_retry(n, max_attempts, last_error)
        if n < max_attempts:
            sleep_fn(interval_seconds)
    return AttemptOutcome(retryable=False, switched=True, attempts=attempts, last_error=last_error)

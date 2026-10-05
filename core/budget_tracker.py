"""
budget_tracker.py — Pantau pemakaian token per provider, tampilkan indikator,
dan picu mode hemat kalau mendekati limit harian.
"""

import tomllib
from pathlib import Path
from core import state

SETTINGS_PATH = Path(__file__).parent.parent / "config" / "settings.toml"
with open(SETTINGS_PATH, "rb") as f:
    _SETTINGS = tomllib.load(f)


def record_usage(provider: str, tokens_used: int, purpose: str = "reasoning"):
    state.log_llm_call(provider, tokens_used, purpose)


def get_status(provider: str) -> dict:
    limit = _SETTINGS["providers"][provider]["daily_token_limit"]
    used = state.tokens_used_today(provider)
    pct = (used / limit * 100) if limit else 0
    return {"provider": provider, "used": used, "limit": limit, "pct": pct}


def format_indicator(provider: str) -> str:
    s = get_status(provider)
    pct = s["pct"]
    icon = "🟢" if pct < 70 else "🟡" if pct < 90 else "🔴"
    warn = " ⚠️ mendekati limit" if pct >= 90 else ""
    used_k = s["used"] // 1000
    limit_k = s["limit"] // 1000
    return f"{icon} [{provider}] {used_k}k/{limit_k}k ({pct:.0f}%){warn}"


def is_over_budget(provider: str) -> bool:
    return get_status(provider)["pct"] >= 100


def is_rate_limited() -> bool:
    """Circuit breaker global: terlalu banyak panggilan LLM dalam 1 menit terakhir."""
    limit = _SETTINGS["system"]["llm_call_rate_limit_per_minute"]
    return state.llm_calls_last_minute() >= limit

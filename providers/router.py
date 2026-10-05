"""
router.py — Multi-provider LLM router TANPA litellm.
Kenapa: litellm butuh compile Rust (maturin/cargo) untuk sebagian dependency,
terlalu berat & rapuh di device 32-bit. Ini pakai `requests` murni yang
sudah pasti tersedia di semua arsitektur, tanpa compile apapun.

Cara kerja:
  1. Baca daftar provider dari settings.toml, urutkan by priority.
  2. Coba satu-satu; kalau error/rate-limit -> cooldown provider itu, lanjut ke berikutnya.
  3. Semua provider gagal -> alert, jangan retry loop tanpa henti.
"""

import time
import tomllib
import requests
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from core import budget_tracker, renderer

SETTINGS_PATH = Path(__file__).parent.parent / "config" / "settings.toml"
SECRETS_PATH = Path(__file__).parent.parent / "config" / "secrets.toml"
with open(SETTINGS_PATH, "rb") as f:
    _SETTINGS = tomllib.load(f)

# Overlay secrets: api_key di secrets.toml (gitignored) menimpa settings.toml.
# Prioritas tertinggi: env var DERRY_<PROVIDER>_API_KEY (mis. DERRY_GEMINI_API_KEY).
import os as _os
if SECRETS_PATH.exists():
    with open(SECRETS_PATH, "rb") as f:
        _secrets = tomllib.load(f)
    for _prov, _cfg in _secrets.get("providers", {}).items():
        if _prov in _SETTINGS.get("providers", {}):
            _SETTINGS["providers"][_prov].update(_cfg)
for _prov in _SETTINGS.get("providers", {}):
    _env = _os.environ.get(f"DERRY_{_prov.upper()}_API_KEY")
    if _env:
        _SETTINGS["providers"][_prov]["api_key"] = _env

# Cooldown provider yang baru saja gagal, supaya tidak dicoba lagi tiap event
# (in-memory saja, cukup untuk 1 sesi jalan; reset kalau proses direstart)
_COOLDOWN: dict[str, float] = {}
COOLDOWN_SECONDS = 120


@dataclass
class LLMResult:
    ok: bool
    provider: str
    text: str = ""
    tokens_used: int = 0
    error: str = ""


def _is_cooling_down(provider: str) -> bool:
    until = _COOLDOWN.get(provider, 0)
    return time.time() < until


def _set_cooldown(provider: str):
    _COOLDOWN[provider] = time.time() + COOLDOWN_SECONDS


def _sorted_providers() -> list[str]:
    providers = _SETTINGS["providers"]
    return sorted(providers.keys(), key=lambda p: providers[p]["priority"])


# === Adapter per jenis API. Tambah adapter baru di sini kalau ada provider lain ===

def _call_openai_compatible(base_url: str, api_key: str, model: str, prompt: str) -> LLMResult:
    """Dipakai untuk Groq & OpenRouter — keduanya kompatibel format OpenAI."""
    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        if resp.status_code == 429:
            return LLMResult(ok=False, provider="", error="rate_limited")
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        return LLMResult(ok=True, provider="", text=text, tokens_used=tokens)
    except requests.RequestException as e:
        return LLMResult(ok=False, provider="", error=str(e))


def _call_gemini(api_key: str, model: str, prompt: str) -> LLMResult:
    model_name = model.split("/")[-1]  # "gemini/gemini-flash-latest" -> "gemini-flash-latest"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    try:
        resp = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "X-goog-api-key": api_key,
            },
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        if resp.status_code == 429:
            return LLMResult(ok=False, provider="", error="rate_limited")
        resp.raise_for_status()
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)
        return LLMResult(ok=True, provider="", text=text, tokens_used=tokens)
    except requests.RequestException as e:
        return LLMResult(ok=False, provider="", error=str(e))


def _call_provider(provider: str, prompt: str) -> LLMResult:
    cfg = _SETTINGS["providers"][provider]
    api_key = cfg.get("api_key", "")
    model = cfg["model"]
    if not api_key or api_key.startswith("ISI_"):
        return LLMResult(ok=False, provider=provider, error="api_key belum diisi")

    if provider == "gemini":
        result = _call_gemini(api_key, model, prompt)
    elif cfg.get("api_base"):
        # Semua provider OpenAI-compatible (groq, openrouter, atria, cohere,
        # llm7, ollama) cukup definisikan api_base di settings.toml
        result = _call_openai_compatible(cfg["api_base"], api_key, model, prompt)
    else:
        return LLMResult(ok=False, provider=provider, error=f"adapter untuk '{provider}' belum ada")

    result.provider = provider
    return result


def complete(prompt: str, purpose: str = "reasoning") -> LLMResult:
    """
    Entry point utama. Coba provider berurutan sesuai priority,
    skip yang lagi cooldown, catat token usage, return hasil pertama yang sukses.
    """
    if budget_tracker.is_rate_limited():
        return LLMResult(ok=False, provider="", error="circuit_breaker: terlalu banyak call/menit")

    for provider in _sorted_providers():
        if _is_cooling_down(provider):
            continue
        if budget_tracker.is_over_budget(provider):
            continue

        result = _call_provider(provider, prompt)

        if result.ok:
            budget_tracker.record_usage(provider, result.tokens_used, purpose)
            print(renderer.kv("Provider dipakai", budget_tracker.format_indicator(provider)))
            return result

        # Gagal -> cooldown provider ini, lanjut ke berikutnya
        _set_cooldown(provider)
        print(renderer.kv(f"[{provider}] gagal", result.error))

    return LLMResult(ok=False, provider="", error="semua provider gagal/cooldown")


def handle(event, decision):
    """Dipanggil dari event_bus.py saat reflex bilang 'needs_llm'."""
    purpose = "triage"  # nanti bisa dibedakan triage vs reasoning sesuai kompleksitas event
    result = complete(event.payload, purpose=purpose)

    if not result.ok:
        print(renderer.alert(f"LLM gagal total untuk event dari {event.source}: {result.error}"))
        return

    print(renderer.section(f"Hasil LLM ({result.provider})"))
    print(result.text)
    # TODO: lanjut ke actions/approval_gate.py sesuai isi keputusan LLM

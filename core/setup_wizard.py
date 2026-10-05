"""
setup_wizard.py — Wizard setup interaktif Derry (Fase 1B).

  derry setup  -> pandu isi API key per provider, tulis ke secrets.toml
Bisa dijalankan ulang kapan saja untuk update key.
"""
import tomllib
from pathlib import Path

from core import renderer

BASE = Path(__file__).parent.parent
CFG = BASE / "config"
SETTINGS_PATH = CFG / "settings.toml"
SECRETS_PATH = CFG / "secrets.toml"

# Petunjuk singkat per provider (tampil di wizard)
HINTS = {
    "atria": "Gratis — daftar di atria-asi.ai",
    "gemini": "Gratis — Google AI Studio (aistudio.google.com)",
    "groq": "Gratis — console.groq.com",
    "openrouter": "Isi saldo — openrouter.ai",
    "cohere": "Gratis tier — dashboard.cohere.com",
    "llm7": "API key dari llm7.io",
    "ollama": "Ollama Cloud — ollama.com (API key)",
}


def _load():
    with open(SETTINGS_PATH, "rb") as f:
        settings = tomllib.load(f)
    secrets = {}
    if SECRETS_PATH.exists():
        with open(SECRETS_PATH, "rb") as f:
            secrets = tomllib.load(f)
    return settings, secrets


def _mask(v: str) -> str:
    if not v or v.startswith("ISI_"):
        return "(belum diisi)"
    return f"*** ({len(v)} char)"


def run():
    settings, secrets = _load()
    providers = sorted(settings.get("providers", {}),
                       key=lambda p: settings["providers"][p].get("priority", 99))

    print(renderer.banner())
    print(renderer.section("Setup Derry"))
    print("Isi API key per provider. Kosongkan + Enter untuk lewati / pertahankan.\n")

    updated = {}
    for prov in providers:
        # key efektif saat ini (secrets menimpa settings)
        cur = secrets.get("providers", {}).get(prov, {}).get("api_key", "")
        if not cur:
            cur = settings["providers"][prov].get("api_key", "")
        hint = HINTS.get(prov, "")
        print(renderer.kv(f"[{prov}]", f"{_mask(cur)}  {hint}"))
        try:
            inp = input(f"  API key {prov} (Enter=lewati): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nDibatalkan.")
            return
        if inp:
            updated[prov] = inp
            print(renderer.kv("  ->", "tersimpan (sementara)"))
        print()

    if not updated:
        print("Tidak ada perubahan.")
        return

    # Tulis ke secrets.toml
    for prov, key in updated.items():
        secrets.setdefault("providers", {}).setdefault(prov, {})["api_key"] = key

    lines = ["# === DERRY SECRETS ===",
             "# File ini JANGAN di-commit (sudah di .gitignore).", ""]
    for prov, pcfg in secrets.get("providers", {}).items():
        lines.append(f"[providers.{prov}]")
        for k, v in pcfg.items():
            lines.append(f'{k} = "{v}"' if isinstance(v, str) else f"{k} = {v}")
        lines.append("")
    SECRETS_PATH.write_text("\n".join(lines))
    SECRETS_PATH.chmod(0o600)

    print(renderer.section("Selesai"))
    print(renderer.kv("Diperbarui", f"{len(updated)} provider: {', '.join(updated)}"))
    print(renderer.kv("Tes cepat", "jalankan: derry config list"))

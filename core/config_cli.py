"""
config_cli.py — CLI konfigurasi Derry (Fase 1A).

  derry config list                  Tampilkan semua config (key disamarkan)
  derry config get <path>            Ambil nilai, mis. providers.gemini.model
  derry config set <path> <value>    Ubah nilai; *.api_key -> secrets.toml

Path memakai notasi titik: providers.gemini.priority, system.debounce_window_seconds
"""
import tomllib
from pathlib import Path

from core import renderer

BASE = Path(__file__).parent.parent
CFG = BASE / "config"
SETTINGS_PATH = CFG / "settings.toml"
SECRETS_PATH = CFG / "secrets.toml"


def _load():
    with open(SETTINGS_PATH, "rb") as f:
        settings = tomllib.load(f)
    secrets = {}
    if SECRETS_PATH.exists():
        with open(SECRETS_PATH, "rb") as f:
            secrets = tomllib.load(f)
    # Gabung untuk baca (secrets menimpa)
    merged = {k: (v.copy() if isinstance(v, dict) else v) for k, v in settings.items()}
    for prov, pcfg in secrets.get("providers", {}).items():
        merged.setdefault("providers", {}).setdefault(prov, {}).update(pcfg)
    return settings, secrets, merged


def _mask(v: str) -> str:
    if not v or v.startswith("ISI_"):
        return "(belum diisi)"
    return f"*** ({len(v)} char)"


def _parse_value(raw: str):
    low = raw.lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _dump_toml(data: dict) -> str:
    lines = []
    for section, sdata in data.items():
        if isinstance(sdata, dict) and any(isinstance(v, dict) for v in sdata.values()):
            for sub, ssub in sdata.items():
                lines.append(f"[{section}.{sub}]")
                for k, v in ssub.items():
                    lines.append(f'{k} = "{v}"' if isinstance(v, str) else f"{k} = {v}")
                lines.append("")
        elif isinstance(sdata, dict):
            lines.append(f"[{section}]")
            for k, v in sdata.items():
                lines.append(f'{k} = "{v}"' if isinstance(v, str) else f"{k} = {v}")
            lines.append("")
    return "\n".join(lines)


def cmd_list():
    settings, secrets, merged = _load()
    print(renderer.section("Konfigurasi Derry"))
    for prov in sorted(merged.get("providers", {}),
                       key=lambda p: merged["providers"][p].get("priority", 99)):
        pcfg = merged["providers"][prov]
        key = pcfg.get("api_key", "")
        print(renderer.kv(f"[{prov}]",
                          f"model={pcfg.get('model')} prio={pcfg.get('priority')} "
                          f"key={_mask(key)}"))
    for section in ("triage", "reasoning", "system"):
        if section in merged:
            print(renderer.kv(f"[{section}]",
                              ", ".join(f"{k}={v}" for k, v in merged[section].items())))


def cmd_get(path: str):
    _, _, merged = _load()
    node = merged
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            print(renderer.alert(f"Path tidak ditemukan: {path}"))
            return
        node = node[part]
    if path.endswith("api_key") and isinstance(node, str):
        node = _mask(node)
    print(f"{path} = {node}")


def cmd_set(path: str, raw_value: str):
    parts = path.split(".")
    if len(parts) < 2:
        print(renderer.alert("Format: <section>.<key> atau providers.<nama>.<key>"))
        return
    value = _parse_value(raw_value)

    # *.api_key -> secrets.toml, sisanya -> settings.toml
    if parts[-1] == "api_key":
        target_path = SECRETS_PATH
        with open(target_path, "rb") as f:
            data = tomllib.load(f)
        # path: providers.<nama>.api_key
        if len(parts) != 3 or parts[0] != "providers":
            print(renderer.alert("api_key hanya untuk providers.<nama>.api_key"))
            return
        data.setdefault("providers", {}).setdefault(parts[1], {})["api_key"] = value
    else:
        target_path = SETTINGS_PATH
        with open(target_path, "rb") as f:
            data = tomllib.load(f)
        node = data
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = value

    # Tulis ulang file terkait (tanpa menghapus section lain)
    if target_path == SECRETS_PATH:
        lines = ["# === DERRY SECRETS ===",
                 "# File ini JANGAN di-commit (sudah di .gitignore).", ""]
        for prov, pcfg in data.get("providers", {}).items():
            lines.append(f"[providers.{prov}]")
            for k, v in pcfg.items():
                lines.append(f'{k} = "{v}"' if isinstance(v, str) else f"{k} = {v}")
            lines.append("")
        target_path.write_text("\n".join(lines))
        target_path.chmod(0o600)
    else:
        # settings: tulis ulang penuh dari data yang sudah dimuat
        with open(SETTINGS_PATH, "rb") as f:
            full = tomllib.load(f)
        # terapkan perubahan ke full
        node = full
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = value
        lines = ["# === DERRY SETTINGS ===",
                 "# API key asli ada di config/secrets.toml (gitignored).",
                 "# File ini aman di-commit.", ""]
        for prov in sorted(full.get("providers", {}),
                           key=lambda p: full["providers"][p].get("priority", 99)):
            pcfg = full["providers"][prov]
            lines.append(f"[providers.{prov}]")
            for k in ("model", "api_base", "daily_token_limit", "priority"):
                if k in pcfg:
                    v = pcfg[k]
                    lines.append(f'{k} = "{v}"' if isinstance(v, str) else f"{k} = {v}")
            lines.append('api_key = ""')
            lines.append("")
        # Section lain (triage, reasoning, system, ui, ...) ditulis generik
        # agar section baru seperti [ui] tidak hilang.
        for section, sdata in full.items():
            if section == "providers" or not isinstance(sdata, dict):
                continue
            lines.append(f"[{section}]")
            for k, v in sdata.items():
                lines.append(f'{k} = "{v}"' if isinstance(v, str) else f"{k} = {v}")
            lines.append("")
        SETTINGS_PATH.write_text("\n".join(lines))

    shown = _mask(value) if parts[-1] == "api_key" else value
    print(renderer.kv("Diset", f"{path} = {shown}"))

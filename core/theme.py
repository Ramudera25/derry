"""
theme.py — Tema warna Derry (Fase 3C).

Empat tema: red (default), gold, emerald, blue.
Tema aktif dibaca dari settings.toml -> [ui] theme.
Ubah via: ./derry config set ui.theme gold
"""
import tomllib
from pathlib import Path

THEMES = {
    "red":     {"accent": "bold red",    "dim": "red",    "ansi": "\033[1;31m"},
    "gold":    {"accent": "bold yellow", "dim": "yellow", "ansi": "\033[1;33m"},
    "emerald": {"accent": "bold green",  "dim": "green",  "ansi": "\033[1;32m"},
    "blue":    {"accent": "bold blue",   "dim": "blue",   "ansi": "\033[1;34m"},
}
DEFAULT = "red"
_SETTINGS = Path.home() / "derry" / "config" / "settings.toml"


def current_name() -> str:
    """Nama tema aktif dari settings.toml."""
    try:
        with open(_SETTINGS, "rb") as f:
            cfg = tomllib.load(f)
        name = str(cfg.get("ui", {}).get("theme", DEFAULT)).lower()
        return name if name in THEMES else DEFAULT
    except Exception:
        return DEFAULT


def accent() -> str:
    """Style rich untuk aksen tema aktif."""
    return THEMES[current_name()]["accent"]


def dim() -> str:
    """Style rich untuk aksen redup tema aktif."""
    return THEMES[current_name()]["dim"]


def ansi() -> str:
    """Kode ANSI aksen (fallback tanpa rich)."""
    return THEMES[current_name()]["ansi"]

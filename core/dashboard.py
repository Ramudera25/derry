"""
dashboard.py — Dashboard status Derry (Fase 3B).

  ./derry status

Menampilkan: banner, tabel provider (model, status key, budget),
status Termux:API, tema aktif, jumlah skill, dan info sesi.
"""
from pathlib import Path

from core import renderer, theme, budget_tracker
from core.config_cli import _load
from actions.termux import api_available


def show() -> None:
    print(renderer.banner())
    print(renderer.section("Provider"))

    settings, secrets, merged = _load()
    providers = merged.get("providers", {})

    table_data = {}
    for name in sorted(providers, key=lambda n: providers[n].get("priority", 99)):
        pcfg = providers[name]
        key = str(pcfg.get("api_key", ""))
        try:
            st = budget_tracker.get_status(name)
            budget = "%d/%d" % (st.get("used", 0), st.get("limit", 0)) if st.get("limit") else "-"
        except Exception:
            budget = "-"
        table_data[name] = (pcfg.get("model", "?"), bool(key), budget)
    print(renderer.provider_table(table_data))

    print(renderer.section("Sistem"))
    print(renderer.kv("Termux:API", "terinstall" if api_available() else "tidak ada"))
    print(renderer.kv("Tema", theme.current_name()))

    from core import skills as skills_mod
    print(renderer.kv("Skill", str(len(skills_mod.list_skills()))))

    sessions = list((Path.home() / "derry" / "sessions").glob("*.json"))
    print(renderer.kv("Sesi chat", str(len(sessions))))
    print(renderer.line())

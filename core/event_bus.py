"""
event_bus.py — Semua sense WAJIB lapor ke sini, tidak boleh langsung ke router/actions.
Tanggung jawab: dedup, debounce, tempel trust_level, lalu teruskan ke reflex.py.
"""

from dataclasses import dataclass, field
from typing import Literal, Optional
import time
import tomllib
from pathlib import Path

from core import state
from core import reflex
from core import renderer

TrustLevel = Literal["trusted", "untrusted"]

SETTINGS_PATH = Path(__file__).parent.parent / "config" / "settings.toml"
with open(SETTINGS_PATH, "rb") as f:
    _SETTINGS = tomllib.load(f)

DEBOUNCE_WINDOW = _SETTINGS["system"]["debounce_window_seconds"]


@dataclass
class Event:
    source: str                  # nama sense, misal 'notif_listener'
    trust_level: TrustLevel      # 'trusted' | 'untrusted'
    payload: str                 # isi event (teks notifikasi, hasil OCR, dll)
    meta: dict = field(default_factory=dict)   # info tambahan bebas (app_name, sender, dll)


def publish(event: Event) -> Optional[int]:
    """
    Titik masuk tunggal untuk semua sense.
    Return event_id kalau diproses, None kalau di-drop (duplikat).
    """
    content_hash = state.make_hash(event.source, event.payload)

    # 1. Dedup/debounce — cegah event sama diproses berkali-kali dalam window pendek
    if state.is_duplicate(content_hash, DEBOUNCE_WINDOW):
        return None  # sengaja diam, tidak perlu log ulang tiap dedup kena

    # 2. Serahkan ke reflex.py — ini yang putuskan: skip, direct-action, atau naik ke LLM
    decision = reflex.evaluate(event)

    event_id = state.log_event(
        source=event.source,
        trust_level=event.trust_level,
        payload=event.payload,
        handled_by=decision.handled_by,
    )

    if decision.handled_by == "blocked":
        _alert_blocked(event, decision.reason)
        return event_id

    if decision.handled_by in ("reflex_skip", "reflex_direct"):
        # Sudah selesai di level reflex, tidak perlu ke LLM sama sekali (hemat token)
        if decision.handled_by == "reflex_direct":
            decision.execute_direct()
        return event_id

    # decision.handled_by == "needs_llm" -> lempar ke router (diisi saat sambungkan providers/router.py)
    from providers import router  # lazy import biar tidak circular
    router.handle(event, decision)

    return event_id


def _alert_blocked(event: Event, reason: str):
    # TODO: sambungkan ke ntfy.sh saat gateway sudah siap
    detail = f"source={event.source} | {reason}\npayload: {event.payload[:80]}"
    print(renderer.alert(detail))

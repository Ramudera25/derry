"""
system_rules.py — Keputusan berbasis kondisi sistem (baterai, storage, dll).
Semua di sini deterministic, tidak butuh reasoning LLM sama sekali.
"""

from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class MatchResult:
    reason: str
    action: Optional[Callable] = None


def try_match(event) -> Optional[MatchResult]:
    if event.source != "termux_api":
        return None

    kind = event.meta.get("sensor")

    if kind == "battery":
        level = event.meta.get("level", 100)
        if level < 15:
            def _alert_low_battery():
                # TODO: sambungkan ke ntfy.sh
                print(f"[ALERT] Baterai rendah: {level}%")
            return MatchResult(reason=f"baterai {level}% < 15%, alert langsung", action=_alert_low_battery)
        return MatchResult(reason="baterai normal, tidak perlu aksi")

    if kind == "storage":
        free_mb = event.meta.get("free_mb", 9999)
        if free_mb < 500:
            def _alert_low_storage():
                print(f"[ALERT] Storage rendah: {free_mb}MB tersisa")
            return MatchResult(reason="storage rendah, alert langsung", action=_alert_low_storage)
        return MatchResult(reason="storage cukup, tidak perlu aksi")

    return None

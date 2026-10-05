"""
ui_patterns.py — Pola elemen UI yang sudah dikenal (dari dump XML rish).
Kalau task UI sudah pernah "dipelajari" polanya, tidak perlu LLM lihat ulang tiap kali.
Juga dipakai approval_gate untuk GROUNDING: cross-check klaim LLM vs dump XML aktual.
"""

from dataclasses import dataclass
from typing import Optional, Callable

# Contoh: mapping task dikenal -> urutan aksi tetap (diisi seiring waktu dari log)
KNOWN_UI_FLOWS = {
    # "buka_wa_chat_favorit": [...langkah tap tetap...]
}


@dataclass
class MatchResult:
    reason: str
    action: Optional[Callable] = None


def try_match(event) -> Optional[MatchResult]:
    if event.source != "rish_bridge":
        return None

    task_name = event.meta.get("task_name")
    if task_name in KNOWN_UI_FLOWS:
        def _run_known_flow():
            print(f"[UI] Menjalankan flow dikenal: {task_name}")
            # TODO: eksekusi urutan tap/swipe dari KNOWN_UI_FLOWS[task_name]
        return MatchResult(reason=f"flow '{task_name}' sudah dikenal, skip LLM", action=_run_known_flow)

    return None


def verify_element_exists(xml_dump: str, element_desc: str) -> bool:
    """
    Dipakai approval_gate.py untuk grounding:
    cek apakah elemen yang disebut LLM benar-benar ada di dump XML terakhir,
    sebelum aksi tap/swipe dieksekusi.
    """
    return element_desc.lower() in xml_dump.lower()

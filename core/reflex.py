"""
reflex.py — Lapisan paling penting untuk hemat token & keamanan.
Jalan TANPA LLM sama sekali. Tiga kemungkinan hasil:
  1. blocked       -> aturan keras dilanggar, event dihentikan total
  2. reflex_skip   -> event jelas tidak penting, di-drop (0 token)
  3. reflex_direct -> pola dikenali, langsung eksekusi aksi tanpa LLM (0 token)
  4. needs_llm     -> baru boleh naik ke router/LLM
"""

from dataclasses import dataclass
from typing import Callable, Optional

from rules import notif_patterns, system_rules, ui_patterns


@dataclass
class Decision:
    handled_by: str                       # 'blocked' | 'reflex_skip' | 'reflex_direct' | 'needs_llm'
    reason: str = ""
    execute_direct: Optional[Callable] = None


# === SISTEM IMUN: aturan keras, TIDAK BISA di-override oleh LLM/config biasa ===
# Ini dicek PALING PERTAMA, sebelum apapun lain.
def _hard_block_check(event) -> Optional[str]:
    text = event.payload.lower()

    # Larangan mutlak: apapun yang berbau OTP/kode verifikasi/kredensial
    # tidak boleh diteruskan jadi trigger aksi otomatis, titik.
    otp_keywords = ["otp", "kode verifikasi", "kode otp", "verification code", "one-time password"]
    if any(k in text for k in otp_keywords) and event.meta.get("intent") == "forward":
        return "mencoba forward konten OTP/kredensial — dilarang mutlak"

    # Event UNTRUSTED tidak boleh langsung memicu actions.
    # (Dia boleh dibaca/diringkas nanti oleh LLM, tapi flag ini dicek lagi di approval_gate)
    if event.trust_level == "untrusted" and event.meta.get("wants_direct_action"):
        return "event untrusted mencoba memicu aksi langsung tanpa approval"

    return None


def evaluate(event) -> Decision:
    # 1. Cek aturan keras dulu — kalau kena, STOP total, tidak lanjut kemanapun
    block_reason = _hard_block_check(event)
    if block_reason:
        return Decision(handled_by="blocked", reason=block_reason)

    # 2. Triage no-LLM: cek apakah pola event ini sudah dikenali rules/
    for rule_module in (notif_patterns, system_rules, ui_patterns):
        result = rule_module.try_match(event)
        if result is not None:
            if result.action is None:
                # Pola dikenali sebagai "tidak penting" -> drop, hemat token
                return Decision(handled_by="reflex_skip", reason=result.reason)
            else:
                # Pola dikenali DAN sudah tahu aksinya -> eksekusi langsung, skip LLM
                return Decision(
                    handled_by="reflex_direct",
                    reason=result.reason,
                    execute_direct=result.action,
                )

    # 3. Tidak ada pola yang cocok -> baru boleh naik ke LLM
    return Decision(handled_by="needs_llm")

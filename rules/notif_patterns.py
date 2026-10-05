"""
notif_patterns.py — Pattern matching untuk notifikasi umum.
Semakin banyak pola ditambah di sini dari waktu ke waktu (belajar dari log),
semakin jarang Derry perlu panggil LLM untuk notifikasi rutin.
"""

from dataclasses import dataclass
from typing import Optional, Callable

# Package name app yang notifikasinya boleh langsung di-skip tanpa LLM
LOW_VALUE_APPS = {
    "com.android.vending",       # Play Store update
    "com.facebook.katana",       # FB umumnya noise
    "com.game.example",          # ganti sesuai app game/promo yang kamu punya
}

# Kata kunci yang selalu bisa diabaikan tanpa perlu reasoning
IGNORE_KEYWORDS = ["promo", "diskon", "flash sale", "update tersedia"]


@dataclass
class MatchResult:
    reason: str
    action: Optional[Callable] = None   # None = cukup di-skip, tidak None = eksekusi langsung


def try_match(event) -> Optional[MatchResult]:
    if event.source != "notif_listener":
        return None

    app = event.meta.get("app_package", "")
    text = event.payload.lower()

    if app in LOW_VALUE_APPS:
        return MatchResult(reason=f"app {app} termasuk low-value list, di-skip")

    if any(kw in text for kw in IGNORE_KEYWORDS):
        return MatchResult(reason="mengandung keyword promo/update, di-skip")

    # Contoh pola yang SUDAH tahu aksinya tanpa perlu LLM:
    # notifikasi baterai penuh -> tidak perlu apa-apa, cukup dicatat
    if app == "android" and "baterai penuh" in text:
        return MatchResult(reason="notif baterai penuh, tidak perlu aksi")

    # Tidak ada pola cocok -> kembalikan None supaya lanjut ke rule berikutnya / LLM
    return None

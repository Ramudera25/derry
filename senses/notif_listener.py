"""
notif_listener.py — Sense notifikasi Android (Fase 2C).

Membaca notifikasi aktif lewat Termux:API, lalu memfilter
berdasarkan kata kunci.
"""
from actions.termux import notification_list, api_available


def scan_notifications(keywords: list[str] | None = None) -> dict:
    """
    Baca notifikasi aktif. Kalau keywords diberikan, hanya kembalikan
    notifikasi yang judul/isinya mengandung salah satu kata kunci.
    """
    if not api_available():
        return {"ok": False, "error": "Termux:API tidak tersedia"}
    r = notification_list()
    if not r["ok"]:
        return r
    items = r["data"] if isinstance(r["data"], list) else []
    if keywords:
        kw = [k.lower() for k in keywords]
        items = [n for n in items
                 if any(k in str(n.get("title", "")).lower()
                        or k in str(n.get("content", "")).lower()
                        for k in kw)]
    return {"ok": True, "count": len(items), "notifications": items}

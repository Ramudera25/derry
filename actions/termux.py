"""
termux.py — Wrapper Termux:API untuk Derry (Fase 2B).

Semua fungsi aman dipanggil walau Termux:API belum terinstall
(return ok=False dengan pesan jelas).
"""
import json
import shutil
import subprocess

TIMEOUT = 15


def _available(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _run(cmd: list[str]) -> dict:
    if not _available(cmd[0]):
        return {"ok": False, "error": f"{cmd[0]} tidak tersedia (install Termux:API?)"}
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
        return {"ok": proc.returncode == 0,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip()[:300]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def api_available() -> bool:
    """Cek apakah Termux:API terinstall."""
    return _available("termux-battery-status")


def notify(title: str, content: str, nid: str = "derry") -> dict:
    """Kirim notifikasi Android."""
    r = _run(["termux-notification", "--id", nid, "--title", title,
              "--content", content])
    return {"ok": r["ok"], "error": r.get("error", "")}


def notify_remove(nid: str = "derry") -> dict:
    r = _run(["termux-notification-remove", nid])
    return {"ok": r["ok"]}


def toast(text: str, short: bool = True) -> dict:
    """Tampilkan toast singkat."""
    r = _run(["termux-toast"] + (["-s"] if short else []) + [text])
    return {"ok": r["ok"]}


def tts_say(text: str, lang: str = "id") -> dict:
    """Text-to-speech."""
    r = _run(["termux-tts-speak", "-l", lang, text])
    return {"ok": r["ok"]}


def battery() -> dict:
    """Status baterai sebagai dict."""
    r = _run(["termux-battery-status"])
    if not r["ok"]:
        return r
    try:
        return {"ok": True, "data": json.loads(r["stdout"])}
    except json.JSONDecodeError:
        return {"ok": False, "error": "respons baterai tidak valid"}


def vibrate(duration_ms: int = 300) -> dict:
    r = _run(["termux-vibrate", "-d", str(duration_ms)])
    return {"ok": r["ok"]}


def clipboard_get() -> dict:
    r = _run(["termux-clipboard-get"])
    return r


def clipboard_set(text: str) -> dict:
    r = _run(["termux-clipboard-set", text])
    return {"ok": r["ok"]}


def notification_list() -> dict:
    """Daftar notifikasi aktif (untuk notif_listener sense)."""
    # Timeout lebih longgar: di HP load tinggi API bisa lambat
    if not _available("termux-notification-list"):
        return {"ok": False, "error": "termux-notification-list tidak tersedia (install Termux:API?)"}
    try:
        # 10s saja: command ini hang kalau izin akses notifikasi Android
        # belum diberikan ke aplikasi Termux:API
        proc = subprocess.run(["termux-notification-list"], capture_output=True,
                               text=True, timeout=10)
        r = {"ok": proc.returncode == 0, "stdout": proc.stdout.strip(),
             "stderr": proc.stderr.strip()[:300]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}
    if not r["ok"]:
        return r
    try:
        data = json.loads(r["stdout"]) if r["stdout"] else []
        return {"ok": True, "data": data}
    except json.JSONDecodeError:
        return {"ok": False, "error": "respons notifikasi tidak valid"}

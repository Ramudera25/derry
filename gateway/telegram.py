"""
telegram.py — Gateway Telegram untuk Derry (Fase 2C).

Polling-based (tanpa webhook): ambil update via getUpdates, kirim via sendMessage.
Token bot disimpan di config/secrets.toml -> [gateway.telegram] bot_token,
chat_id diisi setelah /start terdeteksi.

Cara pakai:
  from gateway.telegram import Telegram
  tg = Telegram(bot_token, chat_id)
  tg.send("halo dari derry")
  updates = tg.get_updates()   # polling manual
"""
import requests

API = "https://api.telegram.org/bot{}"


class Telegram:
    def __init__(self, bot_token: str, chat_id: str | int = "", timeout: int = 20):
        if not bot_token:
            raise ValueError("bot_token kosong — isi di ./derry setup")
        self.base = API.format(bot_token)
        self.chat_id = chat_id
        self.timeout = timeout
        self._offset = 0

    def _call(self, method: str, **params) -> dict:
        try:
            r = requests.post(f"{self.base}/{method}", json=params,
                              timeout=self.timeout)
            data = r.json()
            return {"ok": data.get("ok", False),
                    "result": data.get("result"),
                    "error": data.get("description", "")}
        except Exception as e:
            return {"ok": False, "result": None, "error": str(e)[:200]}

    def me(self) -> dict:
        """Verifikasi token: info bot."""
        return self._call("getMe")

    def send(self, text: str, chat_id: str | int | None = None) -> dict:
        """Kirim pesan teks."""
        cid = chat_id or self.chat_id
        if not cid:
            return {"ok": False, "error": "chat_id belum diisi"}
        return self._call("sendMessage", chat_id=cid, text=text[:4000])

    def get_updates(self) -> dict:
        """Ambil update baru sejak offset terakhir."""
        r = self._call("getUpdates", offset=self._offset, timeout=10)
        if r["ok"] and r["result"]:
            self._offset = max(u["update_id"] for u in r["result"]) + 1
        return r

    @staticmethod
    def extract_messages(updates: list) -> list[dict]:
        """Sederhanakan update menjadi daftar pesan."""
        out = []
        for u in updates or []:
            m = u.get("message") or {}
            if m.get("text"):
                out.append({
                    "chat_id": m.get("chat", {}).get("id"),
                    "from": m.get("from", {}).get("first_name", ""),
                    "text": m.get("text", ""),
                })
        return out

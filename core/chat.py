"""
chat.py — Mode chat interaktif Derry (Fase 2A).
`derry chat` -> REPL dengan riwayat sesi tersimpan.
"""
import json
import time
from datetime import datetime
from pathlib import Path

from core import renderer
from core import state as _state
from providers import router

SESSIONS_DIR = Path(__file__).parent.parent / "sessions"
MAX_HISTORY_TURNS = 10  # batasi konteks biar hemat token


def _ensure_dir():
    SESSIONS_DIR.mkdir(exist_ok=True)


def _session_path(name: str) -> Path:
    return SESSIONS_DIR / f"{name}.json"


def new_session() -> dict:
    _ensure_dir()
    name = datetime.now().strftime("%Y%m%d-%H%M%S")
    sess = {"name": name, "created": time.time(), "turns": []}
    _save(sess)
    return sess


def load_session(name: str) -> dict | None:
    p = _session_path(name)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def latest_session() -> dict | None:
    _ensure_dir()
    files = sorted(SESSIONS_DIR.glob("*.json"))
    if not files:
        return None
    return json.loads(files[-1].read_text())


def _save(sess: dict):
    _session_path(sess["name"]).write_text(json.dumps(sess, ensure_ascii=False, indent=1))


def _build_prompt(sess: dict, user_input: str) -> str:
    """Rangkai riwayat + input baru jadi satu prompt untuk router."""
    lines = []
    for t in sess["turns"][-MAX_HISTORY_TURNS:]:
        lines.append(f"Pengguna: {t['user']}")
        lines.append(f"Derry: {t['derry']}")
    lines.append(f"Pengguna: {user_input}")
    lines.append("Derry:")
    return "\n".join(lines)


def _cmd_help():
    print(renderer.kv("/help", "tampilkan bantuan ini"))
    print(renderer.kv("/provider", "info provider aktif & budget"))
    print(renderer.kv("/clear", "mulai sesi baru (riwayat diarsip)"))
    print(renderer.kv("/quit", "keluar (sesi tersimpan otomatis)"))


def _cmd_provider():
    from providers.router import _SETTINGS
    from core import budget_tracker
    info = {}
    for p in sorted(_SETTINGS["providers"], key=lambda x: _SETTINGS["providers"][x]["priority"]):
        cfg = _SETTINGS["providers"][p]
        key = cfg.get("api_key", "")
        key_ok = bool(key and not key.startswith("ISI_"))
        info[p] = (cfg["model"], key_ok, budget_tracker.format_indicator(p))
    print(renderer.provider_table(info))


def run(continue_last: bool = False):
    _state.init_db()
    if continue_last:
        sess = latest_session()
        if sess:
            print(renderer.kv("Lanjut sesi", sess["name"]))
        else:
            print("Belum ada sesi tersimpan, buat baru.")
            sess = new_session()
    else:
        sess = new_session()

    print(renderer.banner())
    print(renderer.kv("Sesi", sess["name"]))
    print(renderer.kv("Bantuan", "ketik /help"))
    print(renderer.line())

    while True:
        try:
            user_input = input("\n\u001b[1;32mKamu:\u001b[0m ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input == "/quit" or user_input == "/exit":
            break
        if user_input == "/help":
            _cmd_help()
            continue
        if user_input == "/provider":
            _cmd_provider()
            continue
        if user_input == "/clear":
            sess = new_session()
            print(renderer.kv("Sesi baru", sess["name"]))
            continue
        if user_input.startswith("/"):
            print(renderer.kv("?", "perintah tidak dikenal, /help"))
            continue

        prompt = _build_prompt(sess, user_input)
        with renderer.spinner("Derry berpikir..."):
            result = router.complete(prompt, purpose="chat")

        if not result.ok:
            print(renderer.alert(f"Gagal: {result.error}"))
            continue

        print()
        renderer.console_print("[bold cyan]Derry:[/bold cyan]")
        print(renderer.markdown(result.text))
        sess["turns"].append({"user": user_input, "derry": result.text, "provider": result.provider})
        _save(sess)
        _state.log_event("chat_local", "trusted", user_input[:200], handled_by=f"chat:{result.provider}")

    print(renderer.line())
    print(renderer.kv("Sesi tersimpan", sess["name"]))
    print("Sampai jumpa!")

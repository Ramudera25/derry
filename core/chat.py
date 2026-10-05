"""
chat.py — Mode chat interaktif Derry.

`derry chat` -> REPL dengan riwayat sesi tersimpan + log aktivitas live.
`derry ask "..."` -> jawab satu pertanyaan langsung (tanpa sesi interaktif).
"""
import json
import time
from datetime import datetime
from pathlib import Path

from core import renderer, theme
from core import state as _state
from providers import router
from core import agent as _agent

SESSIONS_DIR = Path(__file__).parent.parent / "sessions"
MAX_HISTORY_TURNS = 10  # batasi konteks biar hemat token

_show_log = True  # toggle via /log


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


def _esc(s: str) -> str:
    """Escape markup rich agar teks error tidak merusak format."""
    try:
        from rich.markup import escape
        return escape(str(s))
    except ImportError:
        return str(s)


def _accent_label(text: str) -> str:
    """Label (Kamu:/Derry:) dengan warna aksen tema aktif."""
    a = theme.accent()
    return f"[{a}]{_esc(text)}[/{a}]"


def log_event(event: str, provider: str, detail: str = ""):
    """Callback log aktivitas live dari router."""
    if not _show_log:
        return
    ts = datetime.now().strftime("%H:%M:%S")
    if event == "try":
        renderer.console_print(f"[dim]{ts} [yellow]→[/yellow] mencoba [bold]{_esc(provider)}[/bold]…[/dim]")
    elif event == "fail":
        renderer.console_print(f"[dim]{ts} [yellow]→[/yellow] [red]{_esc(provider)} gagal[/red]: {_esc(detail)}[/dim]")
    elif event == "skip":
        renderer.console_print(f"[dim]{ts} [yellow]→[/yellow] {_esc(provider)} dilewati ({_esc(detail)})[/dim]")
    elif event == "ok":
        renderer.console_print(f"[dim]{ts} [yellow]→[/yellow] [green]{_esc(provider)} menjawab[/green] ({_esc(detail)})[/dim]")
    elif event == "tool":
        renderer.console_print(f"[dim]{ts} [yellow]→[/yellow] menjalankan tool [bold]{_esc(provider)}[/bold] ({_esc(detail)})[/dim]")


def _cmd_help():
    print(renderer.kv("/help", "tampilkan bantuan ini"))
    print(renderer.kv("/provider", "info provider aktif & budget"))
    print(renderer.kv("/sh <cmd>", "jalankan perintah shell, mis. /sh ls ~/"))
    print(renderer.kv("Tanya langsung", "mis. 'lihat isi ~/ lalu laporkan' — derry pakai tool sendiri"))
    print(renderer.kv("/log", "nyala/matikan log aktivitas"))
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


def _cmd_sh(arg: str):
    from actions import terminal
    if not arg.strip():
        print(renderer.kv("?", "pakai: /sh <perintah>, mis. /sh ls ~/"))
        return
    r = terminal.run(arg.strip())
    if r["stdout"]:
        print(r["stdout"])
    if r["stderr"]:
        print(renderer.kv("stderr", r["stderr"][:500]))
    print(renderer.kv("selesai", f"exit={r['returncode']}" + (" (timeout)" if r["returncode"] == -1 else "")))


def _answer(prompt: str, purpose: str = "chat"):
    """Kirim prompt ke agen (LLM + tool) dengan log live. Return dict hasil."""
    return _agent.complete_with_tools(prompt, purpose=purpose, log=log_event)


def _print_answer(res: dict):
    print()
    renderer.console_print(_accent_label("Derry:"))
    print(renderer.markdown(res["text"]))
    print()
    tools = f" · {res['tools']} tool" if res.get("tools") else ""
    renderer.console_print(
        f"[dim]— via {_esc(res['provider'])} · {res['seconds']:.1f}s · {_esc(str(res['tokens']))} token{tools}[/dim]"
    )


def ask_once(question: str):
    """Mode one-shot: jawab satu pertanyaan, tanpa sesi interaktif."""
    _state.init_db()
    print(renderer.banner())
    res = _answer(question, purpose="ask")
    if not res["ok"]:
        print(renderer.alert(f"Gagal: {res['error']}"))
        return
    _print_answer(res)
    _state.log_event("chat_ask", "trusted", question[:200], handled_by=f"ask:{res['provider']}")


def run(continue_last: bool = False):
    global _show_log
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
    from datetime import datetime as _dt
    _h = _dt.now().hour
    _sapa = "pagi" if _h < 11 else "siang" if _h < 15 else "sore" if _h < 19 else "malam"
    print(renderer.kv("Sesi", sess["name"]))
    renderer.console_print(f"[dim]Selamat {_sapa}! Aku bisa lihat direktori, baca file, jalankan perintah, cek baterai — tinggal minta.[/dim]")
    print(renderer.kv("Bantuan", "ketik /help"))
    print(renderer.line())

    ansi = theme.ansi()
    reset = "\033[0m"

    while True:
        try:
            user_input = input(f"\n{ansi}Kamu:{reset} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input in ("/quit", "/exit"):
            break
        if user_input == "/help":
            _cmd_help()
            continue
        if user_input == "/provider":
            _cmd_provider()
            continue
        if user_input == "/log":
            _show_log = not _show_log
            print(renderer.kv("Log aktivitas", "NYALA" if _show_log else "MATI"))
            continue
        if user_input.startswith("/sh"):
            _cmd_sh(user_input[3:])
            continue
        if user_input == "/clear":
            sess = new_session()
            print(renderer.kv("Sesi baru", sess["name"]))
            continue
        if user_input.startswith("/"):
            print(renderer.kv("?", "perintah tidak dikenal, /help"))
            continue

        prompt = _build_prompt(sess, user_input)
        res = _answer(prompt)

        if not res["ok"]:
            print(renderer.alert(f"Gagal: {res['error']}"))
            continue

        _print_answer(res)
        sess["turns"].append({"user": user_input, "derry": res["text"], "provider": res["provider"]})
        _save(sess)
        _state.log_event("chat_local", "trusted", user_input[:200], handled_by=f"chat:{res['provider']}")

    print(renderer.line())
    print(renderer.kv("Sesi tersimpan", sess["name"]))
    print("Sampai jumpa!")

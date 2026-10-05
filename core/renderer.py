"""
renderer.py — Aksen visual Derry (Fase 3A: Rich TUI + Fase 3C: tema).

API tetap sama (fungsi mengembalikan string siap-print), tapi dirender
pakai `rich` bila tersedia: Panel, Rule, Table, Markdown, Spinner.
Fallback ke ANSI polos kalau rich tidak ada.
Warna aksen mengikuti tema aktif (core.theme).
"""
import shutil

from core import theme

try:
    from rich.console import Console as _Console
    from rich.panel import Panel as _Panel
    from rich.rule import Rule as _Rule
    from rich.table import Table as _Table
    from rich.markdown import Markdown as _Markdown
    from rich.text import Text as _Text
    _RICH = True
    _console = _Console()
except ImportError:
    _RICH = False

# Warna ANSI fallback (dipakai kalau rich tidak ada)
RED = "\033[31m"
BOLD_RED = "\033[1;31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
DIM = "\033[2m"
RESET = "\033[0m"

# Kompatibilitas: dulu aksen hardcoded merah
ACCENT = "bold red"
ACCENT_DIM = "red"


def _render(renderable) -> str:
    """Render objek rich jadi string (agar API lama tetap jalan)."""
    with _console.capture() as cap:
        _console.print(renderable)
    return cap.get().rstrip("\n")


def _width() -> int:
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 60


def line(color: str | None = None, char: str = "─") -> str:
    if _RICH:
        return _render(_Rule(style=theme.dim()))
    c = color or theme.ansi()
    return f"{c}{char * _width()}{RESET}"


def header(title: str, color: str | None = None) -> str:
    if _RICH:
        return _render(_Panel(_Text(title, style=theme.accent(), justify="center"),
                              border_style=theme.dim(), padding=(0, 2)))
    c = color or theme.ansi()
    bar = line(c)
    return f"{bar}\n{c}  {title}{RESET}\n{bar}"


def section(title: str, color: str | None = None) -> str:
    if _RICH:
        d = theme.dim()
        return _render(_Rule(f"[{d}]{title}[/{d}]", style=d))
    w = _width()
    c = color or theme.ansi()
    label = f" {title} "
    pad = max((w - len(label)) // 2, 2)
    return f"{c}{'─' * pad}{label}{'─' * pad}{RESET}"


def kv(key: str, value: str, color: str = DIM) -> str:
    if _RICH:
        return _render(_Text.assemble((f"{key:<14}", "dim"), (": ", "dim"), (str(value), "")))
    return f"{color}{key:<14}{RESET}: {value}"


def alert(message: str) -> str:
    # Alert selalu merah (semantik bahaya), tidak ikut tema
    if _RICH:
        return _render(_Panel(_Text(message, style="bold white"),
                              title="[bold red]ALERT[/bold red]",
                              border_style="bold red"))
    return f"{BOLD_RED}{'─' * _width()}\n  {message}\n{'─' * _width()}{RESET}"


def banner() -> str:
    """Banner ASCII DERRY + subtitle, untuk awal sesi."""
    art = (
        "######  ####### ######  ######  ##   ##\n"
        "##   ## ##      ##   ## ##   ##   ## ##\n"
        "##   ## #####   ######  ######     ####\n"
        "##   ## ##      ##   ## ##   ##     ##\n"
        "######  ####### ##   ## ##   ##     ##"
    )
    if _RICH:
        return _render(_Panel(
            _Text(art + "\nAsisten AI event-driven untuk Termux", style=theme.accent(), justify="center"),
            border_style=theme.dim(), padding=(1, 2)))
    return f"{theme.ansi()}{art}{RESET}\n{DIM}Asisten AI event-driven untuk Termux{RESET}"


def provider_table(providers: dict) -> str:
    """Tabel status provider (nama, model, status key)."""
    if _RICH:
        t = _Table(title="Provider", border_style=theme.dim(), header_style=theme.accent())
        t.add_column("Provider", style="bold")
        t.add_column("Model")
        t.add_column("Key")
        t.add_column("Budget")
        for name, (model, key_ok, budget) in providers.items():
            t.add_row(name, model,
                      "[green]OK[/green]" if key_ok else "[yellow]belum diisi[/yellow]",
                      budget)
        return _render(t)
    rows = [f"{'Provider':<12}{'Model':<28}{'Key':<14}Budget"]
    for name, (model, key_ok, budget) in providers.items():
        rows.append(f"{name:<12}{model:<28}{'OK' if key_ok else '-':<14}{budget}")
    return "\n".join(rows)


def markdown(text: str) -> str:
    """Render teks sebagai Markdown (untuk jawaban LLM)."""
    if _RICH:
        return _render(_Markdown(text))
    return text


def spinner(text: str = "Berpikir..."):
    """Context manager spinner rich. Pakai: with renderer.spinner(): ..."""
    if _RICH:
        d = theme.dim()
        return _console.status(f"[{d}]{text}[/{d}]", spinner="dots")
    # Fallback: dummy context manager
    class _Dummy:
        def __enter__(self): print(f"{DIM}{text}{RESET}")
        def __exit__(self, *a): pass
    return _Dummy()


def console_print(*args, **kwargs):
    """Print langsung via rich console (untuk output kaya)."""
    if _RICH:
        _console.print(*args, **kwargs)
    else:
        print(*args)

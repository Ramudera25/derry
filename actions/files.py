"""
files.py — Operasi file untuk Derry (Fase 2B).

Fungsi aman: baca dibatasi ukuran, tulis dengan konfirmasi direktori,
dan daftar isi direktori.
"""
from pathlib import Path

MAX_READ = 20000  # batas baca per file (char)
HOME = Path.home()


def _resolve(path: str) -> Path:
    """Resolve path relatif terhadap home; tolak path absolut di luar home."""
    p = Path(path)
    if not p.is_absolute():
        p = HOME / p
    p = p.resolve()
    # Keamanan: jangan keluar dari home
    try:
        p.relative_to(HOME.resolve())
    except ValueError:
        raise ValueError(f"akses di luar home ditolak: {path}")
    return p


def read(path: str, max_chars: int = MAX_READ) -> dict:
    try:
        p = _resolve(path)
        if not p.is_file():
            return {"ok": False, "error": "bukan file atau tidak ada"}
        text = p.read_text(errors="replace")
        truncated = len(text) > max_chars
        return {"ok": True, "path": str(p), "content": text[:max_chars],
                "truncated": truncated, "size": len(text)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def write(path: str, content: str, append: bool = False) -> dict:
    try:
        p = _resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with open(p, mode) as f:
            f.write(content)
        return {"ok": True, "path": str(p), "bytes": len(content)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def list_dir(path: str = ".", show_hidden: bool = False) -> dict:
    try:
        p = _resolve(path)
        if not p.is_dir():
            return {"ok": False, "error": "bukan direktori"}
        items = []
        for child in sorted(p.iterdir()):
            if not show_hidden and child.name.startswith("."):
                continue
            items.append({
                "name": child.name,
                "type": "dir" if child.is_dir() else "file",
                "size": child.stat().st_size if child.is_file() else 0,
            })
        return {"ok": True, "path": str(p), "items": items}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def exists(path: str) -> bool:
    try:
        return _resolve(path).exists()
    except ValueError:
        return False

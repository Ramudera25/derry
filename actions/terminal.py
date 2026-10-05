"""
terminal.py — Eksekusi perintah shell (Fase 2B).

Dipakai derry untuk menjalankan perintah di Termux secara terkendali:
timeout, capture output, dan batasan direktori kerja.
"""
import subprocess
from pathlib import Path

DEFAULT_TIMEOUT = 30
MAX_OUTPUT = 8000  # potong output biar tidak membanjiri konteks


def run(cmd: str, timeout: int = DEFAULT_TIMEOUT, cwd: str | None = None) -> dict:
    """
    Jalankan perintah shell. Return dict:
      {ok, returncode, stdout, stderr, truncated}
    """
    try:
        proc = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=cwd or str(Path.home()),
        )
        out, err = proc.stdout or "", proc.stderr or ""
        truncated = False
        if len(out) > MAX_OUTPUT:
            out = out[:MAX_OUTPUT] + f"\n... [dipotong, total {len(proc.stdout)} char]"
            truncated = True
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": out.strip(),
            "stderr": err.strip()[:2000],
            "truncated": truncated,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "returncode": -1, "stdout": "",
                "stderr": f"timeout setelah {timeout}s", "truncated": False}
    except Exception as e:
        return {"ok": False, "returncode": -1, "stdout": "",
                "stderr": str(e)[:500], "truncated": False}

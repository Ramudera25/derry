"""
skills.py — Skill learning system untuk Derry (Fase 2D).

Skill = folder di ~/derry/skills/<nama>/ berisi SKILL.md (wajib)
dan script Python opsional (run.py) yang bisa dipanggil Derry.

Format SKILL.md:
  # Nama Skill
  Deskripsi satu paragraf: kapan skill ini dipakai.
  ## Cara pakai
  Contoh pemanggilan / parameter.

Fungsi:
  list_skills()          -> daftar skill terinstall
  load_skill(name)       -> baca SKILL.md + metadata
  run_skill(name, *args) -> jalankan run.py kalau ada
  create_skill(name, description, code) -> buat skill baru dari chat
"""
from pathlib import Path

SKILLS_DIR = Path.home() / "derry" / "skills"


def _skill_dir(name: str) -> Path:
    return SKILLS_DIR / name


def list_skills() -> list[dict]:
    """Daftar semua skill yang terinstall."""
    if not SKILLS_DIR.is_dir():
        return []
    out = []
    for d in sorted(SKILLS_DIR.iterdir()):
        if not d.is_dir():
            continue
        md = d / "SKILL.md"
        desc = ""
        if md.is_file():
            for line in md.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    desc = line
                    break
        out.append({
            "name": d.name,
            "description": desc[:120],
            "has_runner": (d / "run.py").is_file(),
        })
    return out


def load_skill(name: str) -> dict:
    """Baca definisi skill."""
    d = _skill_dir(name)
    md = d / "SKILL.md"
    if not md.is_file():
        return {"ok": False, "error": f"skill '{name}' tidak ditemukan"}
    return {"ok": True, "name": name,
            "doc": md.read_text()[:4000],
            "has_runner": (d / "run.py").is_file()}


def run_skill(name: str, arg: str = "") -> dict:
    """Jalankan run.py milik skill (kalau ada)."""
    import subprocess
    runner = _skill_dir(name) / "run.py"
    if not runner.is_file():
        return {"ok": False, "error": f"skill '{name}' tidak punya run.py"}
    try:
        proc = subprocess.run(
            ["python3", str(runner), arg], capture_output=True,
            text=True, timeout=60, cwd=str(Path.home() / "derry"))
        return {"ok": proc.returncode == 0,
                "stdout": proc.stdout.strip()[:3000],
                "stderr": proc.stderr.strip()[:500]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "skill timeout (60s)"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


def create_skill(name: str, description: str, code: str = "") -> dict:
    """
    Buat skill baru. Dipakai saat Derry "belajar" sesuatu dari chat.
    code opsional: isi run.py.
    """
    safe = "".join(c for c in name.lower().replace(" ", "-") if c.isalnum() or c in "-_")
    if not safe:
        return {"ok": False, "error": "nama skill tidak valid"}
    d = _skill_dir(safe)
    if d.exists():
        return {"ok": False, "error": f"skill '{safe}' sudah ada"}
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(f"# {name}\n\n{description}\n")
    if code:
        (d / "run.py").write_text(code)
    return {"ok": True, "name": safe, "path": str(d)}

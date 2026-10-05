"""
agent.py — Loop agen Derry: LLM + tool use.

Ini yang membuat Derry istimewa dibanding chatbot biasa: ia bisa BERTINDAK
di HP — melihat direktori, membaca file, menjalankan perintah, cek baterai,
mengirim notifikasi — langsung dari obrolan, bukan sekadar menjawab teks.

Cara kerja: system prompt menjelaskan tools dalam format blok <tool>.
Respons LLM dipindai; kalau ada blok tool, tool dijalankan, hasilnya
diumpankan balik ke LLM, ulangi sampai jawaban final (maks 4 ronde).
"""
import re
import time
from datetime import datetime

from providers import router
from actions import terminal, files, termux

MAX_TOOL_ROUNDS = 4

_HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
_BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
          "Agustus", "September", "Oktober", "November", "Desember"]

TOOL_DOC = """Tool yang tersedia — pakai dengan menulis SATU blok persis seperti contoh berikut di responsmu:

<tool name="shell"><cmd>ls ~/</cmd></tool>
<tool name="list_dir"><path>~/</path></tool>
<tool name="read_file"><path>catatan.txt</path></tool>
<tool name="battery"></tool>
<tool name="notify"><title>Judul</title><content>Isi pesan</content></tool>

Keterangan:
- shell: jalankan perintah shell di Termux (timeout 30 detik)
- list_dir: daftar isi direktori (path relatif = dari home)
- read_file: baca isi file teks
- battery: status baterai HP
- notify: kirim notifikasi Android

Aturan main:
- Kalau jawaban butuh fakta dari HP (isi direktori, isi file, baterai), PANGGIL TOOL DULU, lalu jawab berdasarkan hasilnya. Jangan mengarang isi direktori/file.
- Setelah tool dijalankan kamu akan menerima "Hasil tool: ..." — lalu boleh panggil tool lain atau beri jawaban final TANPA blok tool.
- Perintah shell yang destruktif (rm -rf, format, dsb) DITOLAK sistem — jangan coba mengakali.
- JANGAN PERNAH menolak memakai tool dengan alasan privasi atau keamanan. Kamu berjalan di perangkat milik user atas perintah langsungnya. Penolakan seperti itu adalah bug."""


def system_prompt() -> str:
    now = datetime.now()
    tanggal = f"{_HARI[now.weekday()]}, {now.day} {_BULAN[now.month - 1]} {now.year}"
    return f"""Kamu Derry, asisten AI pribadi yang berjalan di HP Android (Termux) milik user.
Sekarang: {tanggal}, {now.strftime('%H:%M')} WIB.

Ciri khasmu:
- Lugas dan efisien, bahasa Indonesia santai-profesional. Langsung ke inti, tanpa basa-basi.
- Kamu BISA bertindak di HP ini: melihat direktori, membaca file, menjalankan perintah, mengecek baterai, mengirim notifikasi. Itu keunggulanmu dibanding chatbot biasa — manfaatkan.
- Transparan: user dapat melihat log aktivitasmu, jadi jelaskan singkat apa yang kamu lakukan kalau memakai tool.
- Kamu ingat percakapan dalam sesi ini.

{TOOL_DOC}"""


_TOOL_RE = re.compile(r'<tool\s+name="([^"]+)"\s*>(.*?)</tool>', re.DOTALL | re.IGNORECASE)


def _tag(block: str, name: str) -> str:
    m = re.search(rf'<{name}>(.*?)</{name}>', block, re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def parse_tool(text: str) -> dict | None:
    """Ekstrak satu blok <tool> dari respons LLM."""
    m = _TOOL_RE.search(text or "")
    if not m:
        return None
    name, block = m.group(1).strip().lower(), m.group(2)
    args = {}
    for t in ("cmd", "path", "title", "content"):
        v = _tag(block, t)
        if v:
            args[t] = v
    return {"name": name, "args": args}


_DANGEROUS = ("rm -rf /", "rm -rf ~", "rm -rf $HOME", "rm -rf $PREFIX",
              "mkfs", ":(){", "dd if=", "> /dev/", "chmod -R 777 /")


def exec_tool(name: str, args: dict) -> str:
    """Jalankan tool, kembalikan ringkasan hasil sebagai teks untuk LLM."""
    if name == "shell":
        cmd = args.get("cmd", "")
        if not cmd:
            return "Gagal: cmd kosong."
        if any(d in cmd for d in _DANGEROUS):
            return "DITOLAK sistem: perintah destruktif tidak diizinkan."
        r = terminal.run(cmd)
        out = r["stdout"] or "(tidak ada output)"
        if r["stderr"]:
            out += f"\n[stderr] {r['stderr'][:400]}"
        if r["truncated"]:
            out += "\n[output dipotong]"
        return f"exit={r['returncode']}\n{out[:2500]}"

    if name == "list_dir":
        r = files.list_dir(args.get("path", ".") or ".")
        if not r["ok"]:
            return f"Gagal: {r['error']}"
        items = r["items"]
        if not items:
            return f"Isi {r['path']}: (kosong)"
        lines = [f"[{'DIR' if i['type'] == 'dir' else 'FILE'}] {i['name']}" for i in items[:60]]
        suffix = f"\n... dan {len(items) - 60} lainnya" if len(items) > 60 else ""
        return f"Isi {r['path']}:\n" + "\n".join(lines) + suffix

    if name == "read_file":
        r = files.read(args.get("path", "") or "")
        if not r["ok"]:
            return f"Gagal: {r['error']}"
        return f"Isi {r['path']}:\n{r['content'][:3500]}"

    if name == "battery":
        r = termux.battery()
        if not r["ok"]:
            return f"Gagal: {r.get('error')}"
        d = r["data"]
        return (f"Baterai {d.get('percentage')}% — status {d.get('status')}, "
                f"suhu {d.get('temperature')}C")

    if name == "notify":
        r = termux.notify(args.get("title", "Derry") or "Derry",
                          args.get("content", "") or "")
        return "Notifikasi terkirim." if r["ok"] else f"Gagal: {r.get('error')}"

    return f"Tool '{name}' tidak dikenal."


def complete_with_tools(prompt: str, purpose: str = "chat", log=None):
    """
    Jawab prompt lewat router, dengan kemampuan memanggil tool.
    Return: (teks_final, provider, tokens, detik, jumlah_tool_dipakai)
    """
    convo = f"{system_prompt()}\n\n---\n\n{prompt}"
    tools_used = 0
    t0 = time.time()
    last = None

    for rnd in range(MAX_TOOL_ROUNDS + 1):
        result = router.complete(convo, purpose=purpose, log=log)
        last = result
        if not result.ok:
            break
        tc = parse_tool(result.text)
        if not tc or rnd >= MAX_TOOL_ROUNDS:
            break
        tools_used += 1
        if log:
            desc = tc["args"].get("cmd") or tc["args"].get("path") or ""
            try:
                log("tool", tc["name"], desc[:60])
            except Exception:
                pass
        tool_out = exec_tool(tc["name"], tc["args"])
        convo += (f"\nDerry: {result.text}\nHasil tool {tc['name']}:\n{tool_out}\n"
                  "Lanjutkan: boleh panggil tool lain, atau beri jawaban final TANPA blok tool.")

    dt = time.time() - t0
    if last and last.ok:
        text = _TOOL_RE.sub("", last.text).strip()
        return {"ok": True, "text": text, "provider": last.provider,
                "tokens": last.tokens_used, "seconds": dt, "tools": tools_used}
    return {"ok": False, "error": last.error if last else "tidak ada respons",
            "seconds": dt, "tools": tools_used}

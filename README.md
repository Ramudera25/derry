# DERRY

**DERRY** — asisten AI pribadi yang berjalan di Termux (Android). Event-driven,
bisa **bertindak** di HP (lihat direktori, baca file, jalankan perintah, cek
baterai, kirim notifikasi) langsung dari obrolan — bukan sekadar chatbot.

## Fitur

- **Chat interaktif** (`derry chat`) dengan log aktivitas live: terlihat provider
  mana yang dicoba, berapa lama, berapa token, dan tool apa yang dijalankan
- **Agen + tool use**: LLM bisa memanggil `shell`, `list_dir`, `read_file`,
  `battery`, `notify` sendiri saat dibutuhkan (perintah destruktif ditolak)
- **Jawab sekali** (`derry ask "..."`) tanpa masuk sesi interaktif
- **Multi-provider + fallback otomatis**: atria → gemini → llm7 → ollama →
  cohere → openrouter → groq (urutan bisa diubah via config)
- **Config CLI** (`derry config list/get/set`) — API key selalu disimpan
  terpisah di `config/secrets.toml` (gitignored, permission 600)
- **Setup wizard** (`derry setup`) untuk mengisi API key per provider
- **Skills** (`derry skill list/show/run`) — skill = folder berisi `SKILL.md`
  + opsional `run.py`; contoh bawaan: `cek-baterai`
- **Dashboard** (`derry status`): banner, tabel provider + budget token,
  status Termux:API, jumlah skill, sesi tersimpan
- **Tema warna** (`derry theme red|gold|emerald|blue`, default: gold)
- **Senses**: baca notifikasi Android (butuh izin akses notifikasi)
- **Gateway Telegram**: polling `getUpdates`/`sendMessage` (butuh token bot)

## Instalasi (Termux)

```bash
pkg install python git
pip install requests rich tomli  # tomli hanya bila Python < 3.11
git clone https://github.com/Ramudera25/derry ~/derry
ln -sf ~/derry/derry $PREFIX/bin/derry
```

Lalu isi API key:

```bash
derry setup
```

atau satu per satu:

```bash
derry config set providers.gemini.api_key "ISI_KEY_KAMU"
```

> API key **tidak pernah** masuk repo. Yang di-commit hanya `settings.toml`
> (tanpa key) dan `secrets.toml.example`. Key asli tinggal di
> `config/secrets.toml` milikmu.

## Penggunaan

```bash
derry                    # langsung buka chat
derry chat               # chat interaktif
derry chat --continue    # lanjutkan sesi terakhir
derry ask "apa itu fotosintesis?"   # jawab sekali, tanpa sesi
derry status             # dashboard
derry theme gold         # ganti tema
```

Perintah di dalam chat:

| Perintah      | Fungsi                                            |
|---------------|---------------------------------------------------|
| `/help`       | bantuan                                           |
| `/provider`   | info provider aktif & budget token                 |
| `/sh <cmd>`   | jalankan perintah shell, mis. `/sh ls ~/`         |
| `/log`        | nyala/matikan log aktivitas                       |
| `/clear`      | sesi baru (riwayat lama diarsip)                   |
| `/quit`       | keluar (sesi tersimpan otomatis)                   |

Contoh kemampuan agen (cukup ditanya dengan bahasa natural):

- "lihat isi direktori ~ saya lalu laporkan"
- "bacakan file catatan.txt lalu ringkas"
- "baterai hp berapa persen?"
- "kirim notifikasi tulisan 'waktunya istirahat'"

## Arsitektur

```
derry                 # wrapper bash -> main.py
main.py               # CLI: chat, ask, config, setup, skill, theme, status
core/
  agent.py            # loop LLM + tool use (ciri khas Derry)
  chat.py             # REPL + sesi tersimpan (sessions/*.json)
  router -> providers/router.py  # fallback multi-provider, budget, cooldown
  config_cli.py       # derry config (settings vs secrets)
  setup_wizard.py     # derry setup
  skills.py           # skill learning system
  dashboard.py        # derry status
  theme.py            # tema warna
  renderer.py         # Rich TUI + fallback ANSI
  event_bus.py, reflex.py, state.py, budget_tracker.py  # fondasi event-driven
actions/              # tools: terminal, files, termux (Termux:API)
senses/               # notif_listener
gateway/              # telegram (polling)
skills/               # skill bawaan, mis. cek-baterai
config/
  settings.toml       # aman di-commit (tanpa key)
  secrets.toml        # KEY ASLI — gitignored
  secrets.toml.example# template publik
```

## Keamanan

- `config/secrets.toml` dan `sessions/` masuk `.gitignore` — jangan pernah
  di-commit atau dibagikan.
- Tool `shell` menolak perintah destruktif (`rm -rf /`, `mkfs`, `dd`, ...).
- Semua aksi tool tercatat di log aktivitas yang terlihat user.

## Lisensi

MIT — pakai, ubah, bagikan sesukamu.

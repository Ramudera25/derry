"""
main.py — Entry point Derry.

  python main.py                       Chat interaktif (sama dengan 'chat')
  python main.py chat [--continue]   Chat interaktif di terminal
  python main.py ask \"teks\"          Jawab sekali langsung
  python main.py config list         Lihat konfigurasi
  python main.py config get <path>   Ambil nilai config
  python main.py config set <p> <v>  Ubah config (*.api_key -> secrets.toml)
  python main.py setup               Wizard setup interaktif
  python main.py skill list          Daftar skill
  python main.py theme gold          Ganti tema warna
  python main.py status              Dashboard status
  python main.py test                Demo fondasi (event_bus + reflex + router)
"""
import argparse
import sys


def cmd_test():
    """Demo fondasi: event_bus + reflex + state + budget_tracker."""
    from core.event_bus import Event, publish
    from core import budget_tracker, renderer

    print(renderer.header("D.E.R.R.Y — SESSION START"))

    e1 = Event(
        source="notif_listener",
        trust_level="untrusted",
        payload="Diskon 50% khusus hari ini!",
        meta={"app_package": "com.shopee.app"},
    )
    print(renderer.section("Event 1: notif low-value"))
    publish(e1)

    e2 = Event(
        source="termux_api",
        trust_level="trusted",
        payload="battery_status",
        meta={"sensor": "battery", "level": 8},
    )
    print(renderer.section("Event 2: baterai rendah"))
    publish(e2)

    e3 = Event(
        source="telegram_bot",
        trust_level="trusted",
        payload="Tolong ringkas jadwal saya besok",
        meta={},
    )
    print(renderer.section("Event 3: butuh LLM (tes alur fallback)"))
    publish(e3)

    print(renderer.section("Budget Status"))
    print(budget_tracker.format_indicator("gemini"))
    print(renderer.line())


def main():
    ap = argparse.ArgumentParser(prog="derry", description="D.E.R.R.Y — asisten AI event-driven untuk Termux")
    sub = ap.add_subparsers(dest="cmd")

    p_chat = sub.add_parser("chat", help="ngobrol interaktif di terminal")
    p_ask = sub.add_parser("ask", help="jawab satu pertanyaan langsung")
    p_ask.add_argument("text", nargs="+", help="pertanyaan, mis. derry ask \"apa itu fotosintesis?\"")

    p_chat.add_argument("--continue", dest="cont", action="store_true",
                        help="lanjutkan sesi terakhir")

    p_cfg = sub.add_parser("config", help="kelola konfigurasi")
    cfg_sub = p_cfg.add_subparsers(dest="cfg_cmd")
    cfg_sub.add_parser("list", help="tampilkan semua config")
    p_get = cfg_sub.add_parser("get", help="ambil nilai config")
    p_get.add_argument("path", help="mis. providers.gemini.model")
    p_set = cfg_sub.add_parser("set", help="ubah nilai config")
    p_set.add_argument("path", help="mis. providers.gemini.priority")
    p_set.add_argument("value", help="nilai baru")

    p_skill = sub.add_parser("skill", help="kelola skill derry")
    skill_sub = p_skill.add_subparsers(dest="skill_cmd")
    skill_sub.add_parser("list", help="daftar skill terinstall")
    p_show = skill_sub.add_parser("show", help="lihat definisi skill")
    p_show.add_argument("name", help="nama skill")
    p_run = skill_sub.add_parser("run", help="jalankan skill")
    p_run.add_argument("name", help="nama skill")
    p_run.add_argument("arg", nargs="?", default="", help="argumen opsional")

    p_theme = sub.add_parser("theme", help="ganti tema warna")
    p_theme.add_argument("name", nargs="?", default="",
                         help="red/gold/emerald/blue (kosong = tampilkan aktif)")

    sub.add_parser("setup", help="wizard setup interaktif")
    sub.add_parser("status", help="dashboard status derry")
    sub.add_parser("test", help="demo fondasi (event/reflex/router)")

    args = ap.parse_args()

    if args.cmd == "ask":
        from core import chat as chat_mod
        chat_mod.ask_once(" ".join(args.text))
    elif args.cmd == "chat":
        from core import chat as chat_mod
        chat_mod.run(continue_last=args.cont)
    elif args.cmd == "config":
        from core import config_cli
        if args.cfg_cmd == "list" or args.cfg_cmd is None:
            config_cli.cmd_list()
        elif args.cfg_cmd == "get":
            config_cli.cmd_get(args.path)
        elif args.cfg_cmd == "set":
            config_cli.cmd_set(args.path, args.value)
    elif args.cmd == "skill":
        from core import skills
        if args.skill_cmd == "list" or args.skill_cmd is None:
            items = skills.list_skills()
            if not items:
                print("belum ada skill. Buat via chat: 'buatkan skill ...'")
            for s in items:
                tag = "[run]" if s["has_runner"] else "[doc]"
                print("  %-20s %s %s" % (s["name"], tag, s["description"]))
        elif args.skill_cmd == "show":
            r = skills.load_skill(args.name)
            print(r["doc"] if r["ok"] else r["error"])
        elif args.skill_cmd == "run":
            r = skills.run_skill(args.name, args.arg)
            print(r["stdout"] if r["ok"] else "error: %s" % (r.get("error") or r.get("stderr")))
    elif args.cmd == "theme":
        from core import theme as theme_mod
        from core import config_cli
        if not args.name:
            print("tema aktif:", theme_mod.current_name())
            print("pilihan:", ", ".join(sorted(theme_mod.THEMES)))
        elif args.name not in theme_mod.THEMES:
            print("tema tidak dikenal:", args.name)
            print("pilihan:", ", ".join(sorted(theme_mod.THEMES)))
        else:
            config_cli.cmd_set("ui.theme", args.name)
            print("tema diganti ke:", args.name)
    elif args.cmd == "setup":
        from core import setup_wizard
        setup_wizard.run()
    elif args.cmd == "status":
        from core import dashboard
        dashboard.show()
    elif args.cmd == "test":
        cmd_test()
    elif args.cmd is None:
        # Ketik "derry" saja langsung buka chat
        from core import chat as chat_mod
        chat_mod.run()
    else:
        ap.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()

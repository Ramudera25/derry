"""
main.py — Entry point Derry.

  python main.py chat [--continue]   Chat interaktif di terminal
  python main.py test                Demo fondasi (event_bus + reflex + router)
  python main.py                     Bantuan
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
    print(renderer.section("Event 3: butuh LLM (key belum diisi, tes alur fallback)"))
    publish(e3)

    print(renderer.section("Budget Status"))
    print(budget_tracker.format_indicator("gemini"))
    print(renderer.line())


def main():
    ap = argparse.ArgumentParser(prog="derry", description="D.E.R.R.Y — asisten AI event-driven untuk Termux")
    sub = ap.add_subparsers(dest="cmd")

    p_chat = sub.add_parser("chat", help="ngobrol interaktif di terminal")
    p_chat.add_argument("--continue", dest="cont", action="store_true",
                        help="lanjutkan sesi terakhir")

    sub.add_parser("test", help="demo fondasi (event/reflex/router)")

    args = ap.parse_args()

    if args.cmd == "chat":
        from core import chat as chat_mod
        chat_mod.run(continue_last=args.cont)
    elif args.cmd == "test":
        cmd_test()
    else:
        ap.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()

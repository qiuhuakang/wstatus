from __future__ import annotations

import argparse
import sys

from src.pipeline import run_daily_screen, run_intraday_confirm


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Wstatus dual-mode right-side stock screener")
    parser.add_argument("--mode", choices=["daily", "intraday"], default="daily")
    parser.add_argument("--date", default=None, help="Run date in YYYY-MM-DD format")
    parser.add_argument("--screen-date", default=None, help="Daily screen date to confirm during intraday mode")
    parser.add_argument("--settings", default=None, help="Path to settings YAML")
    args = parser.parse_args()

    if args.mode == "daily":
        run_daily_screen(screen_date=args.date, settings_path=args.settings)
    else:
        run_intraday_confirm(
            confirm_date=args.date,
            settings_path=args.settings,
            screen_date=args.screen_date,
        )


if __name__ == "__main__":
    main()

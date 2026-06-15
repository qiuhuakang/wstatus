from __future__ import annotations

from datetime import date
from typing import Any

from src.candidate_pool import build_mode_a_symbols, build_mode_b_candidates
from src.config import load_settings
from src.data_fetcher import (
    fetch_daily_kline,
    fetch_limit_up_pool,
    fetch_realtime_snapshots,
    fetch_strong_trend_pool,
    fetch_trading_calendar,
    resolve_trading_day,
)
from src.html_reporter import export_html_report
from src.intraday_confirm import confirm_pending
from src.reporter import export_csv_report, print_report
from src.storage import init_db, query_pending_confirmations, save_daily_results, save_intraday_results
from src.strategy_a import analyze_mode_a
from src.strategy_b import analyze_mode_b, load_catalyst_pool


def _is_empty_frame(frame: Any) -> bool:
    return frame is None or bool(getattr(frame, "empty", False))


def _warn_data_issue(source: str, exc: Exception) -> None:
    print(f"Data source skipped ({source}): {exc}")


def _resolve_screen_date(requested_date: str) -> str:
    try:
        trade_dates = fetch_trading_calendar()
    except Exception as exc:
        _warn_data_issue("trading_calendar", exc)
        return requested_date

    if not trade_dates:
        return requested_date

    try:
        return resolve_trading_day(trade_dates, requested_date)
    except ValueError as exc:
        _warn_data_issue("trading_calendar", exc)
        return requested_date


def _fetch_limit_pool(screen_date: str) -> Any:
    try:
        return fetch_limit_up_pool(screen_date)
    except Exception as exc:
        _warn_data_issue("limit_up_pool", exc)
        return None


def _fetch_strong_trend_pool() -> Any:
    try:
        return fetch_strong_trend_pool()
    except Exception as exc:
        _warn_data_issue("strong_trend_pool", exc)
        return None


def _fetch_daily_frames(symbols: list[str], calendar_days: int) -> dict[str, Any]:
    frames: dict[str, Any] = {}
    for symbol in symbols:
        try:
            frame = fetch_daily_kline(symbol, calendar_days=calendar_days)
        except Exception as exc:
            _warn_data_issue(f"daily_kline:{symbol}", exc)
            continue
        if not _is_empty_frame(frame):
            frames[symbol] = frame
    return frames


def build_daily_mode_a_candidates(limit_pool: Any, strong_pool: Any, settings: dict[str, Any]) -> list[dict[str, Any]]:
    mode_a = settings["params"]["mode_a"]
    return build_mode_a_symbols(
        limit_pool,
        strong_pool,
        min_amount=mode_a["min_amount"],
        min_rise_pct=mode_a["min_prior_rise_pct"],
        require_rise_pct=False,
        max_strong_candidates=mode_a.get("max_strong_trend_candidates"),
    )


def run_daily_screen_with_inputs(
    screen_date: str,
    mode_a_candidates: list[dict[str, Any]],
    mode_b_candidates: list[dict[str, Any]],
    daily_frames: dict[str, Any],
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for candidate in mode_a_candidates:
        frame = daily_frames.get(candidate["symbol"])
        if _is_empty_frame(frame):
            continue
        results.append(
            analyze_mode_a(
                candidate["symbol"],
                candidate.get("name", ""),
                frame,
                settings["params"]["mode_a"],
            )
        )
    for candidate in mode_b_candidates:
        frame = daily_frames.get(candidate["symbol"])
        if _is_empty_frame(frame):
            continue
        results.append(analyze_mode_b(candidate["catalyst"], frame, settings["params"]["mode_b"]))
    return sorted(
        results,
        key=lambda row: (
            row["group"] != "core",
            row["group"] != "watch",
            -row["score"],
            row["symbol"],
        ),
    )


def run_intraday_confirm_with_inputs(
    pending_rows: list[dict[str, Any]],
    snapshots: dict[str, dict[str, Any]],
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for pending in pending_rows:
        snapshot = snapshots.get(pending["symbol"])
        if snapshot is None:
            results.append(
                {
                    "screen_date": pending["screen_date"],
                    "symbol": pending["symbol"],
                    "name": pending["name"],
                    "mode": pending["mode"],
                    "original_group": pending["group"],
                    "signal_date": pending["signal_date"],
                    "snapshot_time": "",
                    "last_price": 0.0,
                    "pct_chg": 0.0,
                    "amount": 0.0,
                    "volume_ratio": 0.0,
                    "confirmed": False,
                    "confirmation_group": "not_confirmed",
                    "confirmation_reasons": [],
                    "confirmation_fail_reasons": ["快照缺失"],
                }
            )
            continue
        results.append(confirm_pending(pending, snapshot, settings["params"]["intraday"]))
    return results


def run_daily_screen(
    screen_date: str | None = None, settings_path: str | None = None
) -> list[dict[str, Any]]:
    settings = load_settings(settings_path)
    requested_date = screen_date or date.today().isoformat()
    actual_date = _resolve_screen_date(requested_date)
    db_path = settings["paths"]["db"]
    export_dir = settings["paths"]["export_dir"]
    init_db(db_path)

    limit_pool = _fetch_limit_pool(actual_date)
    strong_pool = _fetch_strong_trend_pool()
    mode_a_candidates = build_daily_mode_a_candidates(limit_pool, strong_pool, settings)
    catalyst_rows, catalyst_issues = load_catalyst_pool(settings["paths"]["catalyst_pool"], actual_date)
    mode_b_candidates = build_mode_b_candidates(catalyst_rows)
    all_symbols = sorted({candidate["symbol"] for candidate in mode_a_candidates + mode_b_candidates})
    frames = _fetch_daily_frames(all_symbols, settings["runtime"]["calendar_days"])

    results = run_daily_screen_with_inputs(
        actual_date,
        mode_a_candidates,
        mode_b_candidates,
        frames,
        settings,
    )
    save_daily_results(db_path, actual_date, results)
    print_report(results, f"Wstatus daily screening {actual_date}")
    export_csv_report(results, "daily", actual_date, export_dir)
    export_html_report(results, "daily", actual_date, export_dir)
    if catalyst_issues:
        print(f"Catalyst import issues: {len(catalyst_issues)}")
    return results


def run_intraday_confirm(
    confirm_date: str | None = None,
    settings_path: str | None = None,
    screen_date: str | None = None,
) -> list[dict[str, Any]]:
    settings = load_settings(settings_path)
    today = confirm_date or date.today().isoformat()
    db_path = settings["paths"]["db"]
    export_dir = settings["paths"]["export_dir"]
    init_db(db_path)

    pending_date = screen_date or today
    pending = query_pending_confirmations(db_path, pending_date)
    symbols = sorted({row["symbol"] for row in pending})
    if symbols:
        try:
            snapshots = fetch_realtime_snapshots(symbols)
        except Exception as exc:
            _warn_data_issue("realtime_snapshots", exc)
            snapshots = {}
    else:
        snapshots = {}

    results = run_intraday_confirm_with_inputs(pending, snapshots, settings)
    save_intraday_results(db_path, today, results)
    print_report(results, f"Wstatus intraday confirmation {today}")
    export_csv_report(results, "intraday", today, export_dir)
    export_html_report(results, "intraday", today, export_dir)
    return results

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from src.strategy_common import detect_bullish_doji, detect_shrinking_volume, normalize_daily_frame


REQUIRED_CATALYST_FIELDS = [
    "symbol",
    "name",
    "catalyst_date",
    "catalyst_type",
    "catalyst_summary",
    "drop_reason",
    "drop_reason_reversible",
    "valid_until",
]


def _parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        return None


def load_catalyst_pool(path: str | Path, as_of_date: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    file_path = Path(path)
    if not file_path.exists():
        return [], [{"symbol": "", "issue": "catalyst_pool_missing", "row": {}}]

    as_of = date.fromisoformat(as_of_date)
    valid_rows: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    with file_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for line_no, row in enumerate(reader, start=2):
            issue_parts: list[str] = []
            missing = [field for field in REQUIRED_CATALYST_FIELDS if not row.get(field)]
            if missing:
                issue_parts.append("missing_" + "_".join(missing))

            catalyst_date = _parse_date(row.get("catalyst_date", ""))
            valid_until = _parse_date(row.get("valid_until", ""))
            if catalyst_date is None:
                issue_parts.append("invalid_catalyst_date")
            if valid_until is None:
                issue_parts.append("invalid_valid_until")
            elif valid_until < as_of:
                issue_parts.append("catalyst_expired")

            reversible = _parse_bool(row.get("drop_reason_reversible", ""))
            if not reversible:
                issue_parts.append("drop_reason_not_reversible")

            if issue_parts:
                issues.append({"symbol": row.get("symbol", ""), "line_no": line_no, "issue": ",".join(issue_parts), "row": dict(row)})
                continue

            normalized = dict(row)
            normalized["drop_reason_reversible"] = reversible
            valid_rows.append(normalized)
    return valid_rows, issues


def _score_mode_b(reasons: list[str], soft_fails: list[str], hard_fails: list[str]) -> tuple[str, float]:
    score = 45.0 + len(reasons) * 10.0 - len(soft_fails) * 8.0 - len(hard_fails) * 22.0
    score = max(0.0, min(100.0, score))
    if hard_fails:
        return "excluded", round(score, 1)
    if score >= 75 and not soft_fails:
        return "core", round(score, 1)
    if score >= 55:
        return "watch", round(score, 1)
    return "excluded", round(score, 1)


def analyze_mode_b(catalyst_row: dict[str, Any], daily_df: pd.DataFrame, settings: dict) -> dict:
    df = normalize_daily_frame(daily_df)
    catalyst_date = str(catalyst_row["catalyst_date"])
    after = df[df["trade_date"] >= catalyst_date].copy().reset_index(drop=True)
    reasons: list[str] = ["valid_manual_catalyst"]
    soft_fails: list[str] = []
    hard_fails: list[str] = []

    if len(after) < 3:
        hard_fails.append("not_enough_bars_after_catalyst")
        signal = df.iloc[-1]
        return {
            "symbol": catalyst_row["symbol"],
            "name": catalyst_row["name"],
            "mode": "B",
            "group": "excluded",
            "score": 0.0,
            "signal_date": str(signal["trade_date"]),
            "risk_price": round(float(signal["low"]), 2),
            "buy_observation_price": round(float(signal["close"]), 2),
            "reasons": reasons,
            "fail_reasons": hard_fails,
        }

    crash_window = after.iloc[: settings["crash_window_days"] + 1]
    start_close = float(crash_window.iloc[0]["close"])
    crash_low = float(crash_window["low"].min())
    drop_pct = round((start_close - crash_low) / start_close * 100, 2) if start_close > 0 else 0.0
    crash_low_idx = int(crash_window["low"].idxmin())
    signal_start = crash_low_idx + 1
    signal_end = min(len(after), signal_start + settings["signal_after_crash_days"])
    signal_candidates = after.iloc[signal_start:signal_end]
    if signal_candidates.empty and crash_low_idx > 1:
        prior_crash_window = crash_window.iloc[:crash_low_idx]
        prior_crash_low_idx = int(prior_crash_window["low"].idxmin())
        if crash_low_idx - prior_crash_low_idx <= settings["signal_after_crash_days"]:
            crash_low_idx = prior_crash_low_idx
            crash_low = float(prior_crash_window["low"].min())
            drop_pct = round((start_close - crash_low) / start_close * 100, 2) if start_close > 0 else 0.0
            signal_candidates = after.iloc[signal_start - 1 : signal_start]

    if drop_pct >= settings["min_crash_pct"]:
        reasons.append("sharp_reversible_drop")
    else:
        hard_fails.append("crash_drop_too_small")

    best_signal = None
    for _, candidate in signal_candidates.iterrows():
        doji = detect_bullish_doji(
            candidate,
            max_body_ratio=settings["max_signal_body_ratio"],
            max_amplitude_pct=settings["max_signal_amplitude_pct"],
        )
        crash_volume = float(after.iloc[1 : crash_low_idx + 1]["volume"].mean()) if crash_low_idx >= 1 else float(after.iloc[0]["volume"])
        shrink = detect_shrinking_volume(float(candidate["volume"]), crash_volume, settings["shrink_volume_ratio"])
        if doji["passed"] and shrink:
            best_signal = (candidate, doji, crash_volume)
            break
        if doji["passed"] and not shrink:
            hard_fails.append("signal_volume_not_shrinking")

    if best_signal is None:
        if "signal_volume_not_shrinking" not in hard_fails:
            hard_fails.append("shrinking_doji_not_found")
        signal = after.iloc[-1]
        signal_quality = 1.0
    else:
        signal, doji, crash_volume = best_signal
        signal_quality = doji["body_ratio"]
        reasons.append("shrinking_volume_doji")

    group, score = _score_mode_b(reasons, soft_fails, hard_fails)
    signal_low = round(float(signal["low"]), 2)
    signal_close = round(float(signal["close"]), 2)
    return {
        "symbol": catalyst_row["symbol"],
        "name": catalyst_row["name"],
        "mode": "B",
        "group": group,
        "score": score,
        "signal_date": str(signal["trade_date"]),
        "confirm_date": "",
        "risk_price": signal_low,
        "buy_observation_price": signal_close,
        "reasons": reasons,
        "fail_reasons": soft_fails + hard_fails,
        "catalyst_date": catalyst_row["catalyst_date"],
        "catalyst_type": catalyst_row["catalyst_type"],
        "catalyst_summary": catalyst_row["catalyst_summary"],
        "drop_reason": catalyst_row["drop_reason"],
        "drop_pct": drop_pct,
        "crash_days": max(1, crash_low_idx),
        "shrink_doji_date": str(signal["trade_date"]) if best_signal is not None else "",
        "signal_low": signal_low,
        "signal_close": signal_close,
        "upper_trigger_price": signal_close,
        "signal_doji_quality": signal_quality,
    }

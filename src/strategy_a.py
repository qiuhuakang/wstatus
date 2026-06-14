from __future__ import annotations

import pandas as pd

from src.strategy_common import calc_pullback_pct, detect_bullish_doji, normalize_daily_frame


def _find_prior_high(df: pd.DataFrame, settings: dict) -> dict | None:
    if len(df) < settings["consolidation_min_days"] + 2:
        return None
    signal_idx = len(df) - 1
    search_start = max(0, signal_idx - settings["prior_high_window"])
    search_end = signal_idx - settings["consolidation_min_days"]
    if search_end <= search_start:
        return None
    segment = df.iloc[search_start : search_end + 1]
    idx = int(segment["high"].idxmax())
    high_row = df.loc[idx]
    pre_start = max(0, idx - 20)
    base_close = float(df.iloc[pre_start]["close"])
    rise_pct = (
        round((float(high_row["high"]) - base_close) / base_close * 100, 2)
        if base_close > 0
        else 0.0
    )
    high_to_close_pct = (
        round(
            (float(high_row["close"]) - float(high_row["open"]))
            / float(high_row["open"])
            * 100,
            2,
        )
        if float(high_row["open"]) > 0
        else 0.0
    )
    visibility_source = "limit_or_large_bullish" if high_to_close_pct >= 9.0 else "strong_trend"
    return {
        "idx": idx,
        "date": str(high_row["trade_date"]),
        "price": round(float(high_row["high"]), 2),
        "rise_pct": rise_pct,
        "visibility_source": visibility_source,
    }


def _score_mode_a(passed: list[str], soft_fails: list[str], hard_fails: list[str]) -> tuple[str, float]:
    score = 40.0 + len(passed) * 8.0 - len(soft_fails) * 8.0 - len(hard_fails) * 20.0
    score = max(0.0, min(100.0, score))
    if hard_fails:
        return "excluded", round(score, 1)
    if score >= 75 and not soft_fails:
        return "core", round(score, 1)
    if score >= 55:
        return "watch", round(score, 1)
    return "excluded", round(score, 1)


def analyze_mode_a(symbol: str, name: str, daily_df: pd.DataFrame, settings: dict) -> dict:
    df = normalize_daily_frame(daily_df)
    reasons: list[str] = []
    soft_fails: list[str] = []
    hard_fails: list[str] = []

    prior = _find_prior_high(df, settings)
    if prior is None:
        return {
            "symbol": symbol,
            "name": name,
            "mode": "A",
            "group": "excluded",
            "score": 0.0,
            "signal_date": "",
            "risk_price": 0.0,
            "buy_observation_price": 0.0,
            "reasons": [],
            "fail_reasons": ["prior_high_not_found"],
        }

    signal = df.iloc[-1]
    consolidation = df.iloc[prior["idx"] + 1 :]
    consolidation_days = len(consolidation)
    consolidation_low = round(float(consolidation["low"].min()), 2)
    pullback_pct = calc_pullback_pct(prior["price"], consolidation_low)
    signal_check = detect_bullish_doji(
        signal,
        max_body_ratio=settings["max_signal_body_ratio"],
        max_amplitude_pct=settings["max_signal_amplitude_pct"],
    )
    avg_consolidation_volume = (
        float(consolidation.iloc[:-1]["volume"].mean())
        if len(consolidation) > 1
        else float(signal["volume"])
    )
    volume_ok = float(signal["volume"]) <= avg_consolidation_volume * settings["volume_shrink_threshold"]

    if prior["rise_pct"] >= settings["min_prior_rise_pct"]:
        reasons.append("prior_high_has_height")
    else:
        soft_fails.append("prior_high_height_weak")

    if prior["visibility_source"] == "limit_or_large_bullish":
        reasons.append("high_visibility_event")
    else:
        soft_fails.append("visibility_weaker_than_core")

    if settings["consolidation_min_days"] <= consolidation_days <= settings["consolidation_max_days"]:
        reasons.append("consolidation_days_valid")
    else:
        hard_fails.append("consolidation_days_out_of_range")

    if pullback_pct <= settings["max_pullback_pct"]:
        reasons.append("pullback_controlled")
    else:
        hard_fails.append("pullback_too_deep")

    if signal_check["passed"]:
        reasons.append("bullish_doji_signal")
    else:
        hard_fails.extend(signal_check["fail_reasons"])

    pre_signal_consolidation = consolidation.iloc[:-1]
    risk_price = (
        round(float(pre_signal_consolidation.iloc[-1]["low"]), 2)
        if len(pre_signal_consolidation) > 0
        else consolidation_low
    )
    if float(signal["low"]) < risk_price:
        hard_fails.append("signal_breaks_consolidation_low")

    if volume_ok:
        reasons.append("volume_not_distributing")
    else:
        soft_fails.append("signal_volume_too_large")

    group, score = _score_mode_a(reasons, soft_fails, hard_fails)
    upper_trigger_price = round(
        float(consolidation["high"].max()) * (1 + settings["upper_trigger_buffer_pct"] / 100),
        2,
    )
    signal_close = round(float(signal["close"]), 2)
    result = {
        "symbol": symbol,
        "name": name,
        "mode": "A",
        "group": group,
        "score": score,
        "signal_date": str(signal["trade_date"]),
        "confirm_date": "",
        "risk_price": risk_price,
        "buy_observation_price": signal_close,
        "reasons": reasons,
        "fail_reasons": soft_fails + hard_fails,
        "prior_high_date": prior["date"],
        "prior_high_price": prior["price"],
        "prior_high_rise_pct": prior["rise_pct"],
        "visibility_source": prior["visibility_source"],
        "consolidation_days": consolidation_days,
        "consolidation_pullback_pct": pullback_pct,
        "consolidation_low": consolidation_low,
        "signal_doji_quality": signal_check["body_ratio"],
        "money_return_estimate": "snapshot_required",
        "signal_low": round(float(signal["low"]), 2),
        "signal_close": signal_close,
        "upper_trigger_price": upper_trigger_price,
    }
    return result

from __future__ import annotations

from typing import Mapping

import pandas as pd


REQUIRED_DAILY_COLUMNS = ["trade_date", "open", "high", "low", "close", "volume", "amount"]


def normalize_daily_frame(df: pd.DataFrame) -> pd.DataFrame:
    missing = [col for col in REQUIRED_DAILY_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"daily frame missing columns: {missing}")
    result = df.copy()
    result["trade_date"] = result["trade_date"].astype(str)
    result = result.sort_values("trade_date").reset_index(drop=True)
    result["pct_chg"] = result["close"].pct_change().fillna(0.0) * 100
    result["amplitude"] = ((result["high"] - result["low"]) / result["close"].shift(1)).fillna(0.0) * 100
    return result


def calc_body_ratio(row: Mapping[str, float]) -> float:
    high = float(row["high"])
    low = float(row["low"])
    if high <= low:
        return 1.0
    body = abs(float(row["close"]) - float(row["open"]))
    return round(body / (high - low), 3)


def calc_amplitude_pct(row: Mapping[str, float]) -> float:
    close = float(row["close"])
    if close <= 0:
        return 0.0
    return round((float(row["high"]) - float(row["low"])) / close * 100, 2)


def calc_pullback_pct(prior_high: float, current_low: float) -> float:
    if prior_high <= 0:
        return 0.0
    return round((prior_high - current_low) / prior_high * 100, 2)


def detect_bullish_doji(
    row: Mapping[str, float],
    max_body_ratio: float,
    max_amplitude_pct: float,
) -> dict:
    fail_reasons: list[str] = []
    if float(row["close"]) <= float(row["open"]):
        fail_reasons.append("收盘未高于开盘")
    body_ratio = calc_body_ratio(row)
    if body_ratio > max_body_ratio:
        fail_reasons.append("实体太大")
    amplitude_pct = calc_amplitude_pct(row)
    if amplitude_pct > max_amplitude_pct:
        fail_reasons.append("振幅过大")
    return {
        "passed": len(fail_reasons) == 0,
        "body_ratio": body_ratio,
        "amplitude_pct": amplitude_pct,
        "fail_reasons": fail_reasons,
    }


def detect_shrinking_volume(signal_volume: float, baseline_volume: float, threshold: float) -> bool:
    if baseline_volume <= 0:
        return False
    return signal_volume / baseline_volume <= threshold

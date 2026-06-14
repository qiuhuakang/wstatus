import pandas as pd

from src.strategy_common import (
    calc_body_ratio,
    calc_pullback_pct,
    detect_bullish_doji,
    detect_shrinking_volume,
    normalize_daily_frame,
)


def test_detect_bullish_doji_accepts_small_green_body():
    row = {"open": 10.0, "high": 10.8, "low": 9.8, "close": 10.2, "volume": 1000}
    result = detect_bullish_doji(row, max_body_ratio=0.35, max_amplitude_pct=12.0)
    assert result["passed"] is True
    assert result["body_ratio"] == 0.2


def test_detect_bullish_doji_rejects_red_body():
    row = {"open": 10.3, "high": 10.8, "low": 9.8, "close": 10.1, "volume": 1000}
    result = detect_bullish_doji(row, max_body_ratio=0.35, max_amplitude_pct=12.0)
    assert result["passed"] is False
    assert "close_not_above_open" in result["fail_reasons"]


def test_detect_shrinking_volume_compares_signal_to_baseline():
    assert detect_shrinking_volume(signal_volume=600, baseline_volume=1000, threshold=0.75) is True
    assert detect_shrinking_volume(signal_volume=900, baseline_volume=1000, threshold=0.75) is False


def test_calc_pullback_pct_from_prior_high_to_low():
    assert calc_pullback_pct(prior_high=20.0, current_low=17.0) == 15.0


def test_normalize_daily_frame_sorts_and_adds_pct_change():
    df = pd.DataFrame(
        [
            {"trade_date": "2026-06-03", "open": 11, "high": 12, "low": 10, "close": 11, "volume": 100, "amount": 1000},
            {"trade_date": "2026-06-01", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 100, "amount": 1000},
            {"trade_date": "2026-06-02", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 100, "amount": 1000},
        ]
    )
    normalized = normalize_daily_frame(df)
    assert normalized["trade_date"].tolist() == ["2026-06-01", "2026-06-02", "2026-06-03"]
    assert normalized["pct_chg"].round(2).tolist() == [0.0, 5.0, 4.76]

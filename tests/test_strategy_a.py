import pandas as pd

from src.strategy_a import analyze_mode_a


SETTINGS = {
    "prior_high_window": 60,
    "min_prior_rise_pct": 18.0,
    "min_amount": 100000000,
    "consolidation_min_days": 3,
    "consolidation_max_days": 15,
    "max_pullback_pct": 18.0,
    "max_signal_body_ratio": 0.35,
    "max_signal_amplitude_pct": 9.0,
    "volume_shrink_threshold": 1.10,
    "upper_trigger_buffer_pct": 1.0,
}


def mode_a_frame(signal_close=18.2, signal_open=18.0, signal_low=17.7):
    rows = []
    close = 10.0
    for i in range(20):
        rows.append(
            {
                "trade_date": f"2026-05-{i+1:02d}",
                "open": close,
                "high": close + 0.4,
                "low": close - 0.2,
                "close": close + 0.2,
                "volume": 800,
                "amount": 90000000,
            }
        )
        close += 0.2
    rows.append(
        {
            "trade_date": "2026-05-21",
            "open": 14.0,
            "high": 18.8,
            "low": 13.8,
            "close": 18.0,
            "volume": 3000,
            "amount": 250000000,
        }
    )
    for day, price, volume in [
        ("2026-05-22", 17.6, 1800),
        ("2026-05-25", 17.8, 1500),
        ("2026-05-26", 17.7, 1300),
        ("2026-05-27", 17.9, 1200),
    ]:
        rows.append(
            {
                "trade_date": day,
                "open": price - 0.1,
                "high": price + 0.35,
                "low": price - 0.35,
                "close": price,
                "volume": volume,
                "amount": 160000000,
            }
        )
    rows.append(
        {
            "trade_date": "2026-05-28",
            "open": signal_open,
            "high": 18.6,
            "low": signal_low,
            "close": signal_close,
            "volume": 1250,
            "amount": 180000000,
        }
    )
    return pd.DataFrame(rows)


def test_analyze_mode_a_returns_core_for_clean_chip_consolidation():
    result = analyze_mode_a("000001", "Alpha", mode_a_frame(), SETTINGS)
    assert result["group"] == "core"
    assert result["mode"] == "A"
    assert result["signal_date"] == "2026-05-28"
    assert result["risk_price"] == 17.55
    assert result["upper_trigger_price"] > result["signal_close"]
    assert "bullish_doji_signal" in result["reasons"]


def test_analyze_mode_a_returns_watch_for_non_limit_strong_trend():
    df = mode_a_frame()
    df.loc[df["trade_date"] == "2026-05-21", "high"] = 17.0
    df.loc[df["trade_date"] == "2026-05-21", "close"] = 16.5
    result = analyze_mode_a("000002", "Beta", df, SETTINGS)
    assert result["group"] == "watch"
    assert "visibility_weaker_than_core" in result["fail_reasons"]


def test_analyze_mode_a_excludes_when_signal_breaks_consolidation_low():
    result = analyze_mode_a(
        "000003",
        "Gamma",
        mode_a_frame(signal_low=16.0, signal_close=16.4, signal_open=16.2),
        SETTINGS,
    )
    assert result["group"] == "excluded"
    assert "signal_breaks_consolidation_low" in result["fail_reasons"]

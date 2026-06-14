from pathlib import Path

import pandas as pd

from src.strategy_b import analyze_mode_b, load_catalyst_pool


SETTINGS = {
    "crash_window_days": 5,
    "min_crash_pct": 14.0,
    "max_signal_body_ratio": 0.30,
    "max_signal_amplitude_pct": 10.0,
    "shrink_volume_ratio": 0.75,
    "signal_after_crash_days": 2,
}


def mode_b_frame(signal_close=8.35, signal_open=8.25, signal_low=8.05, signal_volume=900):
    return pd.DataFrame(
        [
            {"trade_date": "2026-06-10", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.4, "volume": 1000, "amount": 120000000},
            {"trade_date": "2026-06-11", "open": 10.4, "high": 10.6, "low": 9.3, "close": 9.4, "volume": 2400, "amount": 220000000},
            {"trade_date": "2026-06-12", "open": 9.2, "high": 9.3, "low": 8.1, "close": 8.2, "volume": 2600, "amount": 230000000},
            {"trade_date": "2026-06-15", "open": signal_open, "high": 8.55, "low": signal_low, "close": signal_close, "volume": signal_volume, "amount": 95000000},
        ]
    )


def catalyst():
    return {
        "symbol": "300000",
        "name": "Catalyst",
        "catalyst_date": "2026-06-10",
        "catalyst_type": "order",
        "catalyst_summary": "large contract",
        "drop_reason": "sector selloff",
        "drop_reason_reversible": True,
        "valid_until": "2026-06-25",
        "notes": "manual check",
    }


def test_load_catalyst_pool_accepts_valid_rows(tmp_path):
    path = tmp_path / "catalyst_pool.csv"
    path.write_text(
        "symbol,name,catalyst_date,catalyst_type,catalyst_summary,drop_reason,drop_reason_reversible,valid_until,notes\n"
        "300000,Catalyst,2026-06-10,order,large contract,sector selloff,true,2026-06-25,manual check\n",
        encoding="utf-8",
    )
    rows, issues = load_catalyst_pool(path, as_of_date="2026-06-14")
    assert len(rows) == 1
    assert issues == []
    assert rows[0]["drop_reason_reversible"] is True


def test_load_catalyst_pool_reports_expired_and_irreversible_rows(tmp_path):
    path = tmp_path / "catalyst_pool.csv"
    path.write_text(
        "symbol,name,catalyst_date,catalyst_type,catalyst_summary,drop_reason,drop_reason_reversible,valid_until,notes\n"
        "300001,Expired,2026-06-01,order,old,sector,false,2026-06-05,old row\n",
        encoding="utf-8",
    )
    rows, issues = load_catalyst_pool(path, as_of_date="2026-06-14")
    assert rows == []
    assert issues[0]["symbol"] == "300001"
    assert "drop_reason_not_reversible" in issues[0]["issue"]
    assert "catalyst_expired" in issues[0]["issue"]


def test_analyze_mode_b_returns_core_for_crash_and_shrinking_doji():
    result = analyze_mode_b(catalyst(), mode_b_frame(), SETTINGS)
    assert result["group"] == "core"
    assert result["mode"] == "B"
    assert result["signal_date"] == "2026-06-15"
    assert result["risk_price"] == 8.05
    assert "shrinking_volume_doji" in result["reasons"]


def test_analyze_mode_b_excludes_when_signal_volume_does_not_shrink():
    result = analyze_mode_b(catalyst(), mode_b_frame(signal_volume=2300), SETTINGS)
    assert result["group"] == "excluded"
    assert "signal_volume_not_shrinking" in result["fail_reasons"]

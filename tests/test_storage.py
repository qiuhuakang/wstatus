from pathlib import Path

from src.storage import (
    init_db,
    query_pending_confirmations,
    save_daily_results,
    save_intraday_results,
)


def daily_result():
    return {
        "symbol": "000001",
        "name": "Alpha",
        "mode": "A",
        "group": "core",
        "score": 88.0,
        "signal_date": "2026-06-14",
        "confirm_date": "",
        "risk_price": 10.0,
        "buy_observation_price": 10.8,
        "reasons": ["bullish_doji_signal"],
        "fail_reasons": [],
        "signal_low": 10.0,
        "signal_close": 10.8,
        "upper_trigger_price": 11.0,
    }


def test_save_daily_results_creates_pending_rows(tmp_path):
    db_path = tmp_path / "main.db"
    init_db(db_path)
    save_daily_results(db_path, "2026-06-14", [daily_result()])
    pending = query_pending_confirmations(db_path, "2026-06-14")
    assert len(pending) == 1
    assert pending[0]["symbol"] == "000001"
    assert pending[0]["mode"] == "A"


def test_save_intraday_results_persists_confirmation(tmp_path):
    db_path = tmp_path / "main.db"
    init_db(db_path)
    save_intraday_results(
        db_path,
        "2026-06-15",
        [
            {
                "screen_date": "2026-06-14",
                "symbol": "000001",
                "name": "Alpha",
                "mode": "A",
                "original_group": "core",
                "signal_date": "2026-06-14",
                "snapshot_time": "2026-06-15 14:30:00",
                "last_price": 11.0,
                "pct_chg": 2.0,
                "amount": 100000000,
                "volume_ratio": 1.1,
                "confirmed": True,
                "confirmation_group": "confirmed_core",
                "confirmation_reasons": ["mode_a_trigger_reached"],
                "confirmation_fail_reasons": [],
            }
        ],
    )
    assert Path(db_path).exists()

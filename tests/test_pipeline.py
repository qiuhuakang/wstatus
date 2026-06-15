import pandas as pd

from src.pipeline import (
    build_daily_mode_a_candidates,
    run_daily_screen_with_inputs,
    run_intraday_confirm_with_inputs,
)


def mode_a_frame():
    rows = []
    close = 10.0
    for i in range(20):
        rows.append({"trade_date": f"2026-05-{i+1:02d}", "open": close, "high": close + 0.4, "low": close - 0.2, "close": close + 0.2, "volume": 800, "amount": 90000000})
        close += 0.2
    rows.append({"trade_date": "2026-05-21", "open": 14.0, "high": 18.8, "low": 13.8, "close": 18.0, "volume": 3000, "amount": 250000000})
    for day, price, volume in [
        ("2026-05-22", 17.6, 1800),
        ("2026-05-25", 17.8, 1500),
        ("2026-05-26", 17.7, 1300),
        ("2026-05-27", 17.9, 1200),
    ]:
        rows.append({"trade_date": day, "open": price - 0.1, "high": price + 0.35, "low": price - 0.35, "close": price, "volume": volume, "amount": 160000000})
    rows.append({"trade_date": "2026-05-28", "open": 18.0, "high": 18.6, "low": 17.7, "close": 18.2, "volume": 1250, "amount": 180000000})
    return pd.DataFrame(rows)


def settings():
    return {
        "paths": {"db": "", "export_dir": "", "catalyst_pool": ""},
        "params": {
            "mode_a": {
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
                "min_history_bars": 20,
            },
            "mode_b": {
                "crash_window_days": 5,
                "min_crash_pct": 14.0,
                "max_signal_body_ratio": 0.30,
                "max_signal_amplitude_pct": 10.0,
                "shrink_volume_ratio": 0.75,
                "signal_after_crash_days": 2,
            },
            "intraday": {
                "repair_buffer_pct": -1.0,
                "amount_min_ratio": 0.80,
                "volume_ratio_min": 0.80,
            },
        },
    }


def test_run_daily_screen_with_inputs_returns_core_candidate():
    results = run_daily_screen_with_inputs(
        screen_date="2026-05-28",
        mode_a_candidates=[{"symbol": "000001", "name": "Alpha", "source": "limit_up"}],
        mode_b_candidates=[],
        daily_frames={"000001": mode_a_frame()},
        settings=settings(),
    )
    assert results[0]["symbol"] == "000001"
    assert results[0]["group"] == "core"


def test_run_daily_screen_with_inputs_skips_newly_listed_stocks():
    short_frame = mode_a_frame().tail(10).reset_index(drop=True)

    results = run_daily_screen_with_inputs(
        screen_date="2026-05-28",
        mode_a_candidates=[{"symbol": "000001", "name": "Alpha", "source": "limit_up"}],
        mode_b_candidates=[],
        daily_frames={"000001": short_frame},
        settings=settings(),
    )

    assert results == []


def test_build_daily_mode_a_candidates_uses_non_limit_universe():
    strong = pd.DataFrame(
        [
            {"symbol": "000005", "name": "Sideways", "amount": 180000000, "rise_pct": 1.2},
        ]
    )

    candidates = build_daily_mode_a_candidates(None, strong, settings())

    assert candidates == [{"symbol": "000005", "name": "Sideways", "source": "strong_trend"}]


def test_run_intraday_confirm_with_inputs_returns_confirmation():
    pending = [
        {
            "screen_date": "2026-05-28",
            "symbol": "000001",
            "name": "Alpha",
            "mode": "A",
            "group": "core",
            "signal_date": "2026-05-28",
            "signal_low": 17.7,
            "signal_close": 18.2,
            "risk_price": 17.55,
            "upper_trigger_price": 18.5,
            "payload_json": "{}",
        }
    ]
    snapshots = {
        "000001": {
            "symbol": "000001",
            "name": "Alpha",
            "last_price": 18.6,
            "open": 18.0,
            "prev_close": 18.2,
            "high": 18.7,
            "low": 18.0,
            "pct_chg": 2.2,
            "amount": 180000000,
            "volume_ratio": 1.1,
            "snapshot_time": "2026-05-29 14:30:00",
        }
    }
    results = run_intraday_confirm_with_inputs(pending, snapshots, settings())
    assert results[0]["confirmation_group"] == "confirmed_core"

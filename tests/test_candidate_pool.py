import pandas as pd

from src.candidate_pool import build_mode_a_symbols, build_mode_b_candidates


def test_build_mode_a_symbols_prioritizes_limit_up_and_amount():
    limit_up = pd.DataFrame(
        [
            {"浠ｇ爜": "000001", "鍚嶇О": "Alpha", "杩炴澘鏁?": 2},
            {"浠ｇ爜": "000002", "鍚嶇О": "Beta", "杩炴澘鏁?": 1},
        ]
    )
    strong = pd.DataFrame(
        [
            {"symbol": "000002", "name": "Beta", "amount": 200000000, "rise_pct": 22.0},
            {"symbol": "000003", "name": "Gamma", "amount": 250000000, "rise_pct": 25.0},
            {"symbol": "000004", "name": "Weak", "amount": 10000000, "rise_pct": 3.0},
        ]
    )
    result = build_mode_a_symbols(limit_up, strong, min_amount=100000000, min_rise_pct=18.0)
    assert result == [
        {"symbol": "000001", "name": "Alpha", "source": "limit_up"},
        {"symbol": "000002", "name": "Beta", "source": "limit_up"},
        {"symbol": "000003", "name": "Gamma", "source": "strong_trend"},
    ]


def test_build_mode_b_candidates_maps_catalysts_to_symbols():
    rows = [{"symbol": "300000", "name": "Catalyst", "catalyst_date": "2026-06-10"}]
    result = build_mode_b_candidates(rows)
    assert result == [{"symbol": "300000", "name": "Catalyst", "source": "manual_catalyst", "catalyst": rows[0]}]

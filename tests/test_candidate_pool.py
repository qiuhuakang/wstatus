import pandas as pd

from src.candidate_pool import build_mode_a_symbols, build_mode_b_candidates


def test_build_mode_a_symbols_prioritizes_limit_up_and_uses_market_snapshot():
    limit_up = pd.DataFrame(
        [
            {"symbol": "000001", "name": "Alpha", "amount": 200000000},
            {"symbol": "000002", "name": "Beta", "amount": 200000000},
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
        {"symbol": "000003", "name": "Gamma", "source": "market_snapshot"},
    ]


def test_build_mode_a_symbols_scans_all_liquid_market_snapshot_without_amount_top_cutoff():
    market_snapshot = pd.DataFrame(
        [
            {"symbol": "000005", "name": "Sideways", "amount": 180000000, "rise_pct": 1.2},
            {"symbol": "000006", "name": "Quiet", "amount": 90000000, "rise_pct": 2.0},
            {"symbol": "000007", "name": "Liquid", "amount": 260000000, "rise_pct": -0.5},
            {"symbol": "000008", "name": "AlsoLiquid", "amount": 120000000, "rise_pct": 0.1},
        ]
    )

    result = build_mode_a_symbols(
        None,
        market_snapshot,
        min_amount=100000000,
        min_rise_pct=18.0,
        require_rise_pct=False,
    )

    assert result == [
        {"symbol": "000005", "name": "Sideways", "source": "market_snapshot"},
        {"symbol": "000007", "name": "Liquid", "source": "market_snapshot"},
        {"symbol": "000008", "name": "AlsoLiquid", "source": "market_snapshot"},
    ]


def test_build_mode_a_symbols_excludes_untradable_and_illiquid_names():
    limit_up = pd.DataFrame(
        [
            {"symbol": "000001", "name": "Normal", "amount": 200000000},
            {"symbol": "430001", "name": "BSE", "amount": 200000000},
            {"symbol": "000002", "name": "ST Risk", "amount": 200000000},
            {"symbol": "000003", "name": "退市整理", "amount": 200000000},
            {"symbol": "000004", "name": "Thin", "amount": 1000000},
        ]
    )
    strong = pd.DataFrame(
        [
            {"symbol": "000005", "name": "Liquid", "amount": 260000000, "rise_pct": 1.0},
            {"symbol": "830001", "name": "BSE2", "amount": 260000000, "rise_pct": 1.0},
            {"symbol": "000006", "name": "*ST Bad", "amount": 260000000, "rise_pct": 1.0},
            {"symbol": "000007", "name": "LowAmount", "amount": 99999999, "rise_pct": 1.0},
        ]
    )

    result = build_mode_a_symbols(
        limit_up,
        strong,
        min_amount=100000000,
        min_rise_pct=18.0,
        require_rise_pct=False,
    )

    assert result == [
        {"symbol": "000001", "name": "Normal", "source": "limit_up"},
        {"symbol": "000005", "name": "Liquid", "source": "market_snapshot"},
    ]


def test_build_mode_b_candidates_maps_catalysts_to_symbols():
    rows = [{"symbol": "300000", "name": "Catalyst", "catalyst_date": "2026-06-10"}]
    result = build_mode_b_candidates(rows)
    assert result == [{"symbol": "300000", "name": "Catalyst", "source": "manual_catalyst", "catalyst": rows[0]}]


def test_build_mode_b_candidates_excludes_untradable_manual_rows():
    rows = [
        {"symbol": "300000", "name": "Catalyst", "catalyst_date": "2026-06-10"},
        {"symbol": "430001", "name": "BSE", "catalyst_date": "2026-06-10"},
        {"symbol": "000001", "name": "ST Test", "catalyst_date": "2026-06-10"},
        {"symbol": "000002", "name": "退市测试", "catalyst_date": "2026-06-10"},
    ]

    result = build_mode_b_candidates(rows)

    assert result == [{"symbol": "300000", "name": "Catalyst", "source": "manual_catalyst", "catalyst": rows[0]}]

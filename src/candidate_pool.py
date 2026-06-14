from __future__ import annotations

import pandas as pd


def _limit_up_code(row: pd.Series) -> str:
    return str(row.get("浠ｇ爜", row.get("symbol", ""))).zfill(6)


def _limit_up_name(row: pd.Series) -> str:
    return str(row.get("鍚嶇О", row.get("name", "")))


def build_mode_a_symbols(
    limit_up_pool: pd.DataFrame,
    strong_trend_pool: pd.DataFrame,
    min_amount: float,
    min_rise_pct: float,
) -> list[dict]:
    results: list[dict] = []
    seen: set[str] = set()

    if limit_up_pool is not None and not limit_up_pool.empty:
        for _, row in limit_up_pool.iterrows():
            symbol = _limit_up_code(row)
            if symbol in seen:
                continue
            results.append({"symbol": symbol, "name": _limit_up_name(row), "source": "limit_up"})
            seen.add(symbol)

    if strong_trend_pool is not None and not strong_trend_pool.empty:
        for _, row in strong_trend_pool.iterrows():
            symbol = str(row["symbol"]).zfill(6)
            if symbol in seen:
                continue
            if float(row.get("amount", 0)) >= min_amount and float(row.get("rise_pct", 0)) >= min_rise_pct:
                results.append({"symbol": symbol, "name": str(row.get("name", "")), "source": "strong_trend"})
                seen.add(symbol)

    return results


def build_mode_b_candidates(catalyst_rows: list[dict]) -> list[dict]:
    return [
        {
            "symbol": str(row["symbol"]).zfill(6),
            "name": str(row.get("name", "")),
            "source": "manual_catalyst",
            "catalyst": row,
        }
        for row in catalyst_rows
    ]

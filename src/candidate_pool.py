from __future__ import annotations

import pandas as pd


def _limit_up_code(row: pd.Series) -> str:
    return str(row.get("代码", row.get("symbol", ""))).zfill(6)


def _limit_up_name(row: pd.Series) -> str:
    return str(row.get("名称", row.get("name", "")))


def build_mode_a_symbols(
    limit_up_pool: pd.DataFrame,
    strong_trend_pool: pd.DataFrame,
    min_amount: float,
    min_rise_pct: float,
    require_rise_pct: bool = True,
    max_strong_candidates: int | None = None,
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
        strong_rows = strong_trend_pool.copy()
        if "amount" in strong_rows.columns:
            strong_rows = strong_rows.sort_values("amount", ascending=False)
        added = 0
        for _, row in strong_rows.iterrows():
            symbol = str(row["symbol"]).zfill(6)
            if symbol in seen:
                continue
            amount_ok = float(row.get("amount", 0)) >= min_amount
            rise_ok = (not require_rise_pct) or float(row.get("rise_pct", 0)) >= min_rise_pct
            if not (amount_ok and rise_ok):
                continue
            results.append({"symbol": symbol, "name": str(row.get("name", "")), "source": "strong_trend"})
            seen.add(symbol)
            added += 1
            if max_strong_candidates is not None and added >= max_strong_candidates:
                break

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

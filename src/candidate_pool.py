from __future__ import annotations

import pandas as pd


EXCLUDED_PREFIXES = ("4", "8", "9")
EXCLUDED_NAME_MARKERS = ("退市",)


def normalize_symbol(value: object) -> str:
    symbol = str(value or "").strip().lower()
    for prefix in ("sh", "sz", "bj"):
        if symbol.startswith(prefix):
            symbol = symbol[len(prefix):]
            break
    return symbol.zfill(6) if symbol.isdigit() else symbol


def is_excluded_symbol(symbol: str) -> bool:
    normalized = normalize_symbol(symbol)
    return not normalized.isdigit() or normalized.startswith(EXCLUDED_PREFIXES)


def is_excluded_name(name: str) -> bool:
    text = str(name or "").strip().upper()
    return text.startswith(("ST", "*ST")) or any(marker in text for marker in EXCLUDED_NAME_MARKERS)


def _row_amount(row: pd.Series) -> float:
    for key in ("amount", "成交额"):
        if key in row:
            return float(row.get(key) or 0)
    return 0.0


def _is_tradable_candidate(symbol: str, name: str, amount: float | None, min_amount: float | None) -> bool:
    if is_excluded_symbol(symbol) or is_excluded_name(name):
        return False
    if min_amount is not None and amount is not None and amount < min_amount:
        return False
    return True


def _limit_up_code(row: pd.Series) -> str:
    return normalize_symbol(row.get("代码", row.get("symbol", "")))


def _limit_up_name(row: pd.Series) -> str:
    return str(row.get("名称", row.get("name", "")))


def build_mode_a_symbols(
    limit_up_pool: pd.DataFrame,
    market_snapshot: pd.DataFrame,
    min_amount: float,
    min_rise_pct: float,
    require_rise_pct: bool = True,
) -> list[dict]:
    results: list[dict] = []
    seen: set[str] = set()

    if limit_up_pool is not None and not limit_up_pool.empty:
        for _, row in limit_up_pool.iterrows():
            symbol = _limit_up_code(row)
            name = _limit_up_name(row)
            amount = _row_amount(row)
            if not _is_tradable_candidate(symbol, name, amount, min_amount):
                continue
            if symbol in seen:
                continue
            results.append({"symbol": symbol, "name": name, "source": "limit_up"})
            seen.add(symbol)

    if market_snapshot is not None and not market_snapshot.empty:
        for _, row in market_snapshot.iterrows():
            symbol = normalize_symbol(row["symbol"])
            name = str(row.get("name", ""))
            amount = _row_amount(row)
            if not _is_tradable_candidate(symbol, name, amount, min_amount):
                continue
            if symbol in seen:
                continue
            rise_ok = (not require_rise_pct) or float(row.get("rise_pct", 0)) >= min_rise_pct
            if not rise_ok:
                continue
            results.append({"symbol": symbol, "name": name, "source": "market_snapshot"})
            seen.add(symbol)

    return results


def build_mode_b_candidates(catalyst_rows: list[dict]) -> list[dict]:
    return [
        {
            "symbol": normalize_symbol(row["symbol"]),
            "name": str(row.get("name", "")),
            "source": "manual_catalyst",
            "catalyst": row,
        }
        for row in catalyst_rows
        if _is_tradable_candidate(normalize_symbol(row["symbol"]), str(row.get("name", "")), None, None)
    ]

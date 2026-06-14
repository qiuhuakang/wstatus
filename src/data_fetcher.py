from __future__ import annotations

from datetime import datetime, timedelta

import akshare as ak
import pandas as pd


def to_sina_symbol(code: str) -> str:
    value = str(code).strip()
    if value.startswith(("0", "3")):
        return f"sz{value}"
    if value.startswith("6"):
        return f"sh{value}"
    return ""


def fetch_trading_calendar() -> list[str]:
    cal = ak.tool_trade_date_hist_sina()
    return sorted(str(value) for value in cal["trade_date"].tolist())


def resolve_trading_day(trade_dates: list[str], date_str: str) -> str:
    if date_str in trade_dates:
        return date_str
    eligible = [value for value in trade_dates if value < date_str]
    if not eligible:
        raise ValueError(f"no trading day before {date_str}")
    return eligible[-1]


def fetch_daily_kline(code: str, calendar_days: int = 220) -> pd.DataFrame | None:
    sina_symbol = to_sina_symbol(code)
    if not sina_symbol:
        return None
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=calendar_days)).strftime("%Y%m%d")
    df = ak.stock_zh_a_daily(symbol=sina_symbol, start_date=start_date, end_date=end_date, adjust="qfq")
    if df is None or df.empty:
        return None
    result = df.rename(columns={"date": "trade_date"})
    result["trade_date"] = result["trade_date"].astype(str)
    result["pct_chg"] = result["close"].pct_change().fillna(0.0) * 100
    result["amplitude"] = ((result["high"] - result["low"]) / result["close"].shift(1)).fillna(0.0) * 100
    return result.reset_index(drop=True)


def fetch_limit_up_pool(trade_date: str) -> pd.DataFrame:
    return ak.stock_zt_pool_em(date=trade_date.replace("-", ""))


def fetch_realtime_snapshots(symbols: list[str]) -> dict[str, dict]:
    df = ak.stock_zh_a_spot_em()
    if df is None or df.empty:
        return {}
    rows: dict[str, dict] = {}
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for _, row in df.iterrows():
        symbol = str(row.get("浠ｇ爜", ""))
        if symbol not in symbols:
            continue
        prev_close = float(row.get("鏄ㄦ敹", 0) or 0)
        last_price = float(row.get("鏈€鏂颁环", 0) or 0)
        rows[symbol] = {
            "symbol": symbol,
            "name": str(row.get("鍚嶇О", "")),
            "last_price": last_price,
            "open": float(row.get("浠婂紑", 0) or 0),
            "prev_close": prev_close,
            "high": float(row.get("鏈€楂?", 0) or 0),
            "low": float(row.get("鏈€浣?", 0) or 0),
            "pct_chg": float(row.get("娑ㄨ穼骞?", 0) or 0),
            "amount": float(row.get("鎴愪氦棰?", 0) or 0),
            "volume_ratio": float(row.get("閲忔瘮", 0) or 0),
            "snapshot_time": now,
        }
    return rows

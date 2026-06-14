from __future__ import annotations

from typing import Any


def _base_result(pending: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "screen_date": pending["screen_date"],
        "symbol": pending["symbol"],
        "name": pending["name"],
        "mode": pending["mode"],
        "original_group": pending["group"],
        "signal_date": pending["signal_date"],
        "snapshot_time": snapshot.get("snapshot_time", ""),
        "last_price": float(snapshot["last_price"]),
        "pct_chg": float(snapshot["pct_chg"]),
        "amount": float(snapshot.get("amount", 0.0)),
        "volume_ratio": float(snapshot.get("volume_ratio", 0.0)),
        "confirmed": False,
        "confirmation_group": "not_confirmed",
        "confirmation_reasons": [],
        "confirmation_fail_reasons": [],
    }


def confirm_pending(pending: dict[str, Any], snapshot: dict[str, Any], settings: dict) -> dict[str, Any]:
    result = _base_result(pending, snapshot)
    reasons: list[str] = []
    fail_reasons: list[str] = []

    last_price = float(snapshot["last_price"])
    low = float(snapshot["low"])
    signal_low = float(pending["signal_low"])
    signal_close = float(pending["signal_close"])
    upper_trigger = float(pending["upper_trigger_price"])
    volume_ratio = float(snapshot.get("volume_ratio", 0.0))

    if low < signal_low or last_price < float(pending["risk_price"]):
        fail_reasons.append("跌破风控线")

    if pending["mode"] == "A":
        if last_price >= upper_trigger:
            reasons.append("模式A触及触发价")
        elif last_price >= signal_close:
            reasons.append("模式A修复至信号收盘价")
        else:
            fail_reasons.append("模式A价格未修复")
    elif pending["mode"] == "B":
        if low >= signal_low:
            reasons.append("模式B信号低点守住")
        if last_price >= signal_close or float(snapshot["pct_chg"]) >= settings["repair_buffer_pct"]:
            reasons.append("模式B价格修复")
        else:
            fail_reasons.append("模式B价格未修复")
    else:
        fail_reasons.append("未知模式")

    if volume_ratio >= settings["volume_ratio_min"]:
        reasons.append("量比达标")
    else:
        fail_reasons.append("量比不足")

    has_price_confirmation = any(
        reason in reasons
        for reason in (
            "模式A触及触发价",
            "模式A修复至信号收盘价",
            "模式B价格修复",
        )
    )
    confirmed = "跌破风控线" not in fail_reasons and has_price_confirmation
    result["confirmed"] = confirmed
    if confirmed and not fail_reasons:
        result["confirmation_group"] = "confirmed_core" if pending["group"] == "core" else "confirmed_watch"
    elif confirmed:
        result["confirmation_group"] = "confirmed_watch"

    result["confirmation_reasons"] = reasons
    result["confirmation_fail_reasons"] = fail_reasons
    return result

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
        fail_reasons.append("risk_line_broken")

    if pending["mode"] == "A":
        if last_price >= upper_trigger:
            reasons.append("mode_a_trigger_reached")
        elif last_price >= signal_close:
            reasons.append("mode_a_signal_close_repaired")
        else:
            fail_reasons.append("mode_a_price_not_repaired")
    elif pending["mode"] == "B":
        if low >= signal_low:
            reasons.append("mode_b_signal_low_held")
        if last_price >= signal_close or float(snapshot["pct_chg"]) >= settings["repair_buffer_pct"]:
            reasons.append("mode_b_price_repaired")
        else:
            fail_reasons.append("mode_b_price_not_repaired")
    else:
        fail_reasons.append("unknown_mode")

    if volume_ratio >= settings["volume_ratio_min"]:
        reasons.append("volume_ratio_ok")
    else:
        fail_reasons.append("volume_ratio_weak")

    has_price_confirmation = any(
        reason in reasons
        for reason in (
            "mode_a_trigger_reached",
            "mode_a_signal_close_repaired",
            "mode_b_price_repaired",
        )
    )
    confirmed = "risk_line_broken" not in fail_reasons and has_price_confirmation
    result["confirmed"] = confirmed
    if confirmed and not fail_reasons:
        result["confirmation_group"] = "confirmed_core" if pending["group"] == "core" else "confirmed_watch"
    elif confirmed:
        result["confirmation_group"] = "confirmed_watch"

    result["confirmation_reasons"] = reasons
    result["confirmation_fail_reasons"] = fail_reasons
    return result

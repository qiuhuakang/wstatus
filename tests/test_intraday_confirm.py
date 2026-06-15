from src.intraday_confirm import confirm_pending


SETTINGS = {
    "repair_buffer_pct": -1.0,
    "amount_min_ratio": 0.80,
    "volume_ratio_min": 0.80,
}


def pending(mode="A"):
    return {
        "screen_date": "2026-06-14",
        "symbol": "000001",
        "name": "Alpha",
        "mode": mode,
        "group": "core",
        "signal_date": "2026-06-14",
        "signal_low": 10.0,
        "signal_close": 10.8,
        "risk_price": 10.0,
        "upper_trigger_price": 11.0,
        "payload_json": "{}",
    }


def snapshot(last_price=11.05, low=10.55, pct_chg=2.31, volume_ratio=1.1):
    return {
        "symbol": "000001",
        "name": "Alpha",
        "last_price": last_price,
        "open": 10.65,
        "prev_close": 10.8,
        "high": 11.1,
        "low": low,
        "pct_chg": pct_chg,
        "amount": 160000000,
        "volume_ratio": volume_ratio,
        "snapshot_time": "2026-06-15 14:30:00",
    }


def test_confirm_mode_a_core_when_price_breaks_upper_trigger():
    result = confirm_pending(pending("A"), snapshot(), SETTINGS)
    assert result["confirmed"] is True
    assert result["confirmation_group"] == "confirmed_core"
    assert "模式A触及触发价" in result["confirmation_reasons"]


def test_reject_mode_a_when_risk_line_breaks():
    result = confirm_pending(pending("A"), snapshot(last_price=9.9, low=9.8, pct_chg=-8.0), SETTINGS)
    assert result["confirmed"] is False
    assert result["confirmation_group"] == "not_confirmed"
    assert "跌破风控线" in result["confirmation_fail_reasons"]


def test_confirm_mode_b_when_signal_low_holds_and_price_repairs():
    p = pending("B")
    p["upper_trigger_price"] = 10.8
    result = confirm_pending(p, snapshot(last_price=10.9, low=10.1, pct_chg=0.93), SETTINGS)
    assert result["confirmed"] is True
    assert "模式B信号低点守住" in result["confirmation_reasons"]


def test_watch_confirmation_when_volume_is_weak():
    result = confirm_pending(pending("A"), snapshot(volume_ratio=0.4), SETTINGS)
    assert result["confirmed"] is True
    assert result["confirmation_group"] == "confirmed_watch"
    assert "量比不足" in result["confirmation_fail_reasons"]

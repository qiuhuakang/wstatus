from pathlib import Path

from src.html_reporter import export_html_report
from src.reporter import export_csv_report


def result():
    return {
        "symbol": "000001",
        "name": "Alpha",
        "mode": "A",
        "group": "core",
        "score": 88.0,
        "signal_date": "2026-06-14",
        "risk_price": 10.0,
        "buy_observation_price": 10.8,
        "reasons": ["bullish_doji_signal"],
        "fail_reasons": [],
    }


def test_export_csv_report_writes_rows(tmp_path):
    path = export_csv_report([result()], "daily", "2026-06-14", tmp_path)
    text = Path(path).read_text(encoding="utf-8-sig")
    assert "symbol,name,mode,group,score" in text
    assert "000001,Alpha,A,core,88.0" in text


def test_export_html_report_contains_group_and_reason(tmp_path):
    path = export_html_report([result()], "daily", "2026-06-14", tmp_path)
    text = Path(path).read_text(encoding="utf-8")
    assert "Wstatus daily 选股 报告" in text
    assert "bullish_doji_signal" in text

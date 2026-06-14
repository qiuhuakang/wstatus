from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


REPORT_FIELDS = [
    "symbol",
    "name",
    "mode",
    "group",
    "score",
    "signal_date",
    "risk_price",
    "buy_observation_price",
    "reasons",
    "fail_reasons",
]


def _cell(value: Any) -> str:
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    return str(value)


def print_report(results: list[dict[str, Any]], title: str) -> None:
    print("=" * 80)
    print(title)
    print("=" * 80)
    if not results:
        print("No matching candidates.")
        return
    for row in results:
        print(
            f"{row.get('symbol',''):<8} {row.get('name',''):<12} "
            f"{row.get('mode',''):<2} {row.get('group',''):<15} "
            f"{row.get('score',''):<6} risk={row.get('risk_price','')}"
        )


def export_csv_report(
    results: list[dict[str, Any]], report_type: str, report_date: str, export_dir: str | Path
) -> str:
    output_dir = Path(export_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{report_type}_{report_date}.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        for result in results:
            writer.writerow({field: _cell(result.get(field, "")) for field in REPORT_FIELDS})
    latest = output_dir / f"{report_type}_latest.csv"
    latest.write_text(path.read_text(encoding="utf-8-sig"), encoding="utf-8-sig")
    return str(path)

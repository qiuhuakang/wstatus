from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any


GROUP_LABELS = {
    "core": "核心",
    "watch": "关注",
    "excluded": "排除",
    "not_confirmed": "未确认",
}


def _group_label(value: str) -> str:
    return GROUP_LABELS.get(value, value)


def _format_list(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(escape(str(item)) for item in value)
    return escape(str(value))


def export_html_report(
    results: list[dict[str, Any]], report_type: str, report_date: str, export_dir: str | Path
) -> str:
    output_dir = Path(export_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{report_type}_{report_date}.html"
    rows = []
    for result in results:
        rows.append(
            "<tr>"
            f"<td>{escape(str(result.get('symbol', '')))}</td>"
            f"<td>{escape(str(result.get('name', '')))}</td>"
            f"<td>{escape(str(result.get('mode', '')))}</td>"
            f"<td>{escape(_group_label(str(result.get('group', result.get('confirmation_group', '')))))}</td>"
            f"<td>{escape(str(result.get('score', '')))}</td>"
            f"<td>{escape(str(result.get('signal_date', '')))}</td>"
            f"<td>{escape(str(result.get('risk_price', '')))}</td>"
            f"<td>{_format_list(result.get('reasons', result.get('confirmation_reasons', [])))}</td>"
            f"<td>{_format_list(result.get('fail_reasons', result.get('confirmation_fail_reasons', [])))}</td>"
            "</tr>"
        )
    body = "\n".join(rows) if rows else '<tr><td colspan="9">无符合条件的标的</td></tr>'
    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>Wstatus {escape(report_type)} 报告 {escape(report_date)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #222; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background: #f5f5f5; }}
  </style>
</head>
<body>
  <h1>Wstatus {escape(report_type)} 报告 {escape(report_date)}</h1>
  <table>
    <thead>
      <tr><th>代码</th><th>名称</th><th>模式</th><th>分组</th><th>评分</th><th>信号日期</th><th>止损价</th><th>通过条件</th><th>未通过条件</th></tr>
    </thead>
    <tbody>
      {body}
    </tbody>
  </table>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
    latest = output_dir / f"{report_type}_latest.html"
    latest.write_text(html, encoding="utf-8")
    return str(path)

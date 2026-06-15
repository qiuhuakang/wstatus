from __future__ import annotations

import json
from collections import defaultdict
from html import escape
from pathlib import Path
from typing import Any

GROUP_LABELS = {
    "core": "核心",
    "watch": "关注",
    "excluded": "排除",
    "not_confirmed": "未确认",
}

GROUP_ORDER = {"core": 0, "watch": 1, "excluded": 2, "not_confirmed": 3}

GROUP_CSS_CLASS = {
    "core": "passed",
    "watch": "watch",
    "excluded": "excluded",
    "not_confirmed": "pending",
}

GROUP_BORDER_COLOR = {
    "core": "#27ae60",
    "watch": "#2980b9",
    "excluded": "#e74c3c",
    "not_confirmed": "#e67e22",
}

_CN_NUM = [
    "一", "二", "三", "四", "五", "六", "七", "八", "九", "十",
    "十一", "十二", "十三", "十四", "十五",
]


def _group_label(value: str) -> str:
    return GROUP_LABELS.get(value, value)


def _format_list(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(escape(str(item)) for item in value)
    return escape(str(value))


def _group_by_fail_reasons(results: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in results:
        fails = r.get("fail_reasons", [])
        if not fails:
            key = "未分类"
        elif len(fails) == 1:
            key = fails[0]
        else:
            key = " + ".join(fails)
        groups[key].append(r)
    for stocks in groups.values():
        stocks.sort(key=lambda x: x.get("score", 0), reverse=True)
    return dict(
        sorted(groups.items(), key=lambda item: (len(item[0].split(" + ")), item[0]))
    )


def _build_card(
    r: dict[str, Any],
    idx: int | None = None,
    prefix: str = "c",
    show_rank: bool = False,
) -> str:
    code = escape(str(r.get("symbol", "")))
    name = escape(str(r.get("name", "")))[:8]
    mode = escape(str(r.get("mode", "")))
    score = r.get("score", 0)
    signal_date = escape(str(r.get("signal_date", "")))
    risk_price = r.get("risk_price", 0)
    reasons = r.get("reasons", []) or r.get("confirmation_reasons", [])
    fail_reasons = r.get("fail_reasons", []) or r.get("confirmation_fail_reasons", [])
    group = r.get("group", "") or r.get("confirmation_group", "")
    css_class = GROUP_CSS_CLASS.get(group, "excluded")
    card_id = f"card_{prefix}_{code}"

    # Extra detail fields for expanded body
    extra_items: list[str] = []
    if mode == "A":
        if r.get("prior_high_date"):
            extra_items.append(
                f'<div class="detail-item"><span class="detail-label">前期高点日</span><span class="detail-value">{escape(str(r["prior_high_date"]))} (¥{r.get("prior_high_price", "")})</span></div>'
            )
        if r.get("prior_high_rise_pct") is not None:
            extra_items.append(
                f'<div class="detail-item"><span class="detail-label">前期涨幅</span><span class="detail-value">{r["prior_high_rise_pct"]}%</span></div>'
            )
        if r.get("consolidation_days") is not None:
            extra_items.append(
                f'<div class="detail-item"><span class="detail-label">调整天数</span><span class="detail-value">{r["consolidation_days"]}天</span></div>'
            )
        if r.get("consolidation_pullback_pct") is not None:
            extra_items.append(
                f'<div class="detail-item"><span class="detail-label">回调幅度</span><span class="detail-value">{r["consolidation_pullback_pct"]}%</span></div>'
            )
        if r.get("visibility_source"):
            extra_items.append(
                f'<div class="detail-item"><span class="detail-label">可见度</span><span class="detail-value">{escape(str(r["visibility_source"]))}</span></div>'
            )
    elif mode == "B":
        if r.get("catalyst_date"):
            extra_items.append(
                f'<div class="detail-item"><span class="detail-label">催化剂日期</span><span class="detail-value">{escape(str(r["catalyst_date"]))}</span></div>'
            )
        if r.get("catalyst_type"):
            extra_items.append(
                f'<div class="detail-item"><span class="detail-label">催化剂类型</span><span class="detail-value">{escape(str(r["catalyst_type"]))}</span></div>'
            )
        if r.get("catalyst_summary"):
            extra_items.append(
                f'<div class="detail-item"><span class="detail-label">催化剂摘要</span><span class="detail-value">{escape(str(r["catalyst_summary"]))}</span></div>'
            )
        if r.get("drop_pct") is not None:
            extra_items.append(
                f'<div class="detail-item"><span class="detail-label">跌幅</span><span class="detail-value">{r["drop_pct"]}%</span></div>'
            )
        if r.get("crash_days") is not None:
            extra_items.append(
                f'<div class="detail-item"><span class="detail-label">下跌天数</span><span class="detail-value">{r["crash_days"]}天</span></div>'
            )

    rank_html = f'<span class="rank">#{idx}</span>' if show_rank and idx is not None else ""
    mode_badge = f'<span class="mode-badge mode-{mode.lower()}">模式{mode}</span>'

    reasons_str = _format_list(reasons)
    fail_str = _format_list(fail_reasons)

    expanded_body = ""
    if extra_items:
        expanded_body = f"""
          <div class="card-body">
            <div class="detail-grid">
              {"".join(extra_items)}
            </div>
            <div class="detail-reasons">
              <div class="reason-section pass"><b>通过条件：</b>{reasons_str if reasons_str else "—"}</div>
              <div class="reason-section fail"><b>未通过条件：</b>{fail_str if fail_str else "—"}</div>
            </div>
          </div>"""

    return f'''
        <div class="stock-card {css_class}" id="{card_id}" data-symbol="{code}">
          <div class="card-header" onclick="toggleCard(this)">
            <div class="card-left">
              {rank_html}
              <span class="symbol">{code}</span>
              <span class="name">{name}</span>
              {mode_badge}
              <span class="score-badge">{score}分</span>
            </div>
            <div class="card-meta">
              <span>信号日: <b>{signal_date}</b></span>
              <span>止损: <b>¥{risk_price}</b></span>
              <span class="meta-reasons">{reasons_str[:60]}{"…" if len(reasons_str) > 60 else ""}</span>
            </div>
            <span class="expand-icon">▸</span>
          </div>{expanded_body}
        </div>'''


def _build_search_index_js(
    results: list[dict[str, Any]], tab_id_prefix: str
) -> str:
    """Generate JavaScript stock search index."""
    entries = []
    for r in results:
        code = escape(str(r.get("symbol", "")))
        name = escape(str(r.get("name", "")))
        group = r.get("group", "") or r.get("confirmation_group", "")
        tab_id = f"{tab_id_prefix}-{group}"
        tab_name = _group_label(group)
        tab_class = GROUP_CSS_CLASS.get(group, "excluded")
        entries.append(
            f'    _stockIndex["{code}"] = {{ symbol: "{code}", name: "{name}", tabId: "{tab_id}", tabName: "{tab_name}", tabClass: "{tab_class}" }};'
        )
    return "\n".join(entries)


def _build_tab_btn(label: str, tab_id: str, css_class: str, count: int, active: bool = False) -> str:
    active_cls = " active" if active else ""
    return f'<button class="tab-btn {css_class}{active_cls}" onclick="switchTab(\'{tab_id}\')">{label} ({count})</button>'


def _build_html(results: list[dict[str, Any]], report_type: str, report_date: str) -> str:
    is_intraday = report_type == "intraday"

    # Split by group
    core = [r for r in results if r.get("group") == "core" or r.get("confirmation_group") == "core"]
    watch = [r for r in results if r.get("group") == "watch" or r.get("confirmation_group") == "watch"]
    excluded = [r for r in results if r.get("group") == "excluded" or r.get("confirmation_group") == "excluded"]
    not_confirmed = [r for r in results if r.get("group") == "not_confirmed" or r.get("confirmation_group") == "not_confirmed"]

    # Sort by score
    core.sort(key=lambda x: x.get("score", 0), reverse=True)
    watch.sort(key=lambda x: x.get("score", 0), reverse=True)
    excluded.sort(key=lambda x: x.get("score", 0), reverse=True)
    not_confirmed.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Group excluded by fail_reasons
    excluded_groups = _group_by_fail_reasons(excluded)

    # Build card HTML
    def build_cards(stock_list, pfx, show_rank=False):
        return "\n".join(
            _build_card(r, idx=i + 1 if show_rank else None, prefix=pfx, show_rank=show_rank)
            for i, r in enumerate(stock_list)
        )

    # Tabs
    tab_prefix = "tab"
    tabs_html_parts = []
    tab_panes_parts = []

    all_groups = [("core", core, "passed", True), ("watch", watch, "watch", False)]
    if is_intraday:
        all_groups.append(("not_confirmed", not_confirmed, "pending", False))
    all_groups.append(("excluded", excluded, "fail", False))

    first_active = True
    for group_key, group_list, css_class, _ in all_groups:
        tab_id = f"{tab_prefix}-{group_key}"
        label = _group_label(group_key)
        tabs_html_parts.append(_build_tab_btn(label, tab_id, css_class, len(group_list), active=first_active))
        content = ""
        if group_key == "excluded" and excluded_groups:
            content = _build_excluded_groups_html(excluded_groups)
        elif group_list:
            content = build_cards(group_list, group_key[:2], show_rank=(group_key == "core"))
        else:
            content = f'<div class="empty-tab">无{label}标的</div>'
        tab_panes_parts.append(
            f'<div id="{tab_id}" class="tab-content{" active" if first_active else ""}">{content}</div>'
        )
        first_active = False

    # Summary counts
    total = len(results)
    passed_count = len(core) + len(watch)

    # Search index
    search_entries = _build_search_index_js(results, tab_prefix)

    # Title
    title_map = {"daily": "daily 选股", "intraday": "盘中确认"}
    report_title = title_map.get(report_type, report_type)

    # Pre-compute conditional HTML parts
    not_confirmed_card = (
        f'''<div class="summary-card pending">
    <div class="num">{len(not_confirmed)}</div>
    <div class="label">未确认</div>
  </div>'''
        if is_intraday
        else ""
    )

    tabs_html = "".join(tabs_html_parts)
    tab_panes_html = "".join(tab_panes_parts)

    # Tab map indices for JS
    if is_intraday:
        excluded_tab_idx = 3
    else:
        excluded_tab_idx = 2

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Wstatus {escape(report_title)} 报告 - {escape(report_date)}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; background: #f5f6fa; color: #2c3e50; padding-bottom: 40px; }}
.container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
.header {{ background: linear-gradient(135deg, #1a1a2e, #16213e); color: white; padding: 24px 32px; border-radius: 12px; margin-bottom: 20px; }}
.header h1 {{ font-size: 24px; margin-bottom: 6px; }}
.header .date {{ font-size: 14px; color: #a0aec0; }}
.summary {{ display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }}
.summary-card {{ flex: 1; min-width: 120px; background: white; border-radius: 10px; padding: 16px 20px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
.summary-card .num {{ font-size: 32px; font-weight: 700; }}
.summary-card .label {{ font-size: 13px; color: #7f8c8d; margin-top: 4px; }}
.summary-card.pass .num {{ color: #27ae60; }}
.summary-card.watch .num {{ color: #2980b9; }}
.summary-card.fail .num {{ color: #e74c3c; }}
.summary-card.pending .num {{ color: #e67e22; }}
.summary-card.total .num {{ color: #2c3e50; }}

.tabs-wrapper {{ display: flex; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }}
.tabs {{ display: flex; gap: 8px; flex: 1; flex-wrap: wrap; }}
.tab-btn {{ padding: 10px 24px; border: none; border-radius: 20px; font-size: 15px; cursor: pointer; font-weight: 600; transition: all 0.2s; white-space: nowrap; font-family: inherit; }}
.tab-btn.passed {{ background: #eafaf1; color: #27ae60; }}
.tab-btn.passed.active {{ background: #27ae60; color: white; }}
.tab-btn.watch {{ background: #eaf2f8; color: #2980b9; }}
.tab-btn.watch.active {{ background: #2980b9; color: white; }}
.tab-btn.fail {{ background: #fdedec; color: #e74c3c; }}
.tab-btn.fail.active {{ background: #e74c3c; color: white; }}
.tab-btn.pending {{ background: #fef5e7; color: #e67e22; }}
.tab-btn.pending.active {{ background: #e67e22; color: white; }}
.tab-content {{ display: none; }}
.tab-content.active {{ display: block; }}

.search-box {{ position: relative; width: 220px; flex-shrink: 0; }}
.search-input {{ width: 100%; padding: 8px 14px 8px 34px; border: 1px solid #ddd; border-radius: 20px; font-size: 14px; outline: none; font-family: inherit; transition: border-color 0.2s; background: white; }}
.search-input:focus {{ border-color: #1a1a2e; box-shadow: 0 0 0 2px rgba(26,26,46,0.1); }}
.search-input::placeholder {{ color: #bdc3c7; }}
.search-icon {{ position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: #bdc3c7; font-size: 14px; pointer-events: none; }}
.search-dropdown {{ display: none; position: absolute; top: 100%; left: 0; right: 0; margin-top: 4px; background: white; border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.15); max-height: 320px; overflow-y: auto; z-index: 100; }}
.search-dropdown.open {{ display: block; }}
.search-item {{ display: flex; align-items: center; padding: 10px 14px; cursor: pointer; gap: 10px; font-size: 13px; transition: background 0.15s; border-bottom: 1px solid #f0f0f0; }}
.search-item:last-child {{ border-bottom: none; }}
.search-item:hover {{ background: #f5f6fa; }}
.search-item .s-symbol {{ font-weight: 700; color: #2c3e50; min-width: 55px; }}
.search-item .s-name {{ color: #7f8c8d; flex: 1; }}
.search-item .s-tab {{ font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 600; white-space: nowrap; }}
.search-item .s-tab.passed {{ background: #eafaf1; color: #27ae60; }}
.search-item .s-tab.watch {{ background: #eaf2f8; color: #2980b9; }}
.search-item .s-tab.fail {{ background: #fdedec; color: #e74c3c; }}
.search-item .s-tab.pending {{ background: #fef5e7; color: #e67e22; }}
.search-no-result {{ padding: 16px; text-align: center; color: #bdc3c7; font-size: 13px; }}
.search-clear {{ display: none; position: absolute; right: 10px; top: 50%; transform: translateY(-50%); background: none; border: none; color: #bdc3c7; cursor: pointer; font-size: 16px; padding: 0; line-height: 1; }}
.search-clear.visible {{ display: block; }}
.search-clear:hover {{ color: #555; }}

.stock-card.highlight {{ animation: highlightPulse 1.5s ease-in-out; }}
@keyframes highlightPulse {{ 0% {{ box-shadow: 0 0 0 0 rgba(41,128,185,0.5); }} 50% {{ box-shadow: 0 0 0 8px rgba(41,128,185,0); }} 100% {{ box-shadow: 0 1px 4px rgba(0,0,0,0.05); }} }}

.stock-card {{ background: white; border-radius: 8px; margin-bottom: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); overflow: hidden; transition: box-shadow 0.2s; }}
.stock-card:hover {{ box-shadow: 0 2px 12px rgba(0,0,0,0.1); }}
.stock-card.passed {{ border-left: 4px solid #27ae60; }}
.stock-card.watch {{ border-left: 4px solid #2980b9; }}
.stock-card.excluded {{ border-left: 4px solid #e74c3c; }}
.stock-card.pending {{ border-left: 4px solid #e67e22; }}

.card-header {{ display: flex; align-items: center; padding: 12px 16px; cursor: pointer; user-select: none; transition: background 0.15s; gap: 16px; }}
.card-header:hover {{ background: #f8f9fa; }}
.passed .card-header:hover {{ background: #f0faf3; }}
.watch .card-header:hover {{ background: #eaf2f8; }}
.excluded .card-header:hover {{ background: #fef5f5; }}
.pending .card-header:hover {{ background: #fef9f0; }}

.card-left {{ display: flex; align-items: center; gap: 10px; min-width: 280px; }}
.rank {{ font-weight: 700; font-size: 16px; color: #7f8c8d; width: 32px; }}
.symbol {{ font-weight: 700; font-size: 14px; color: #2c3e50; }}
.name {{ font-size: 13px; color: #7f8c8d; }}
.score-badge {{ background: #27ae60; color: white; padding: 2px 10px; border-radius: 12px; font-size: 13px; font-weight: 600; }}
.mode-badge {{ padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }}
.mode-badge.mode-a {{ background: #e8daef; color: #8e44ad; }}
.mode-badge.mode-b {{ background: #d5f5e3; color: #1e8449; }}

.card-meta {{ display: flex; gap: 16px; flex: 1; font-size: 13px; color: #555; flex-wrap: wrap; min-width: 0; }}
.card-meta b {{ color: #2c3e50; }}
.meta-reasons {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 200px; }}

.expand-icon {{ font-size: 14px; color: #bdc3c7; transition: transform 0.2s; width: 20px; text-align: center; flex-shrink: 0; }}
.card-header.expanded .expand-icon {{ transform: rotate(90deg); }}

.card-body {{ display: none; padding: 0 16px 16px; border-top: 1px solid #f0f0f0; }}
.card-body.open {{ display: block; }}

.detail-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 8px; padding: 12px 0; }}
.detail-item {{ background: #f8f9fb; border-radius: 6px; padding: 8px 12px; }}
.detail-label {{ font-size: 11px; color: #7f8c8d; display: block; }}
.detail-value {{ font-size: 13px; font-weight: 600; color: #2c3e50; margin-top: 2px; }}

.detail-reasons {{ margin-top: 8px; display: flex; flex-direction: column; gap: 6px; }}
.reason-section {{ font-size: 13px; padding: 8px 12px; border-radius: 6px; line-height: 1.6; }}
.reason-section.pass {{ background: #eafaf1; color: #27ae60; }}
.reason-section.fail {{ background: #fdedec; color: #e74c3c; }}

.excluded-group {{ margin-bottom: 8px; }}
.group-header {{ display: flex; align-items: center; padding: 10px 16px; background: white; border-radius: 8px; cursor: pointer; user-select: none; border-left: 4px solid #e74c3c; margin-bottom: 4px; }}
.group-header:hover {{ background: #fef5f5; }}
.group-title {{ font-weight: 600; font-size: 14px; color: #2c3e50; flex: 1; }}
.group-count {{ font-size: 13px; color: #e74c3c; font-weight: 600; margin-right: 12px; }}
.group-header .expand-icon {{ font-size: 14px; color: #bdc3c7; transition: transform 0.2s; }}
.group-header.expanded .expand-icon {{ transform: rotate(90deg); }}
.group-body {{ display: none; }}
.group-body.open {{ display: block; }}

.empty-tab {{ padding: 40px; text-align: center; color: #bdc3c7; font-size: 15px; }}

.footer {{ text-align: center; padding: 30px 0 10px; font-size: 12px; color: #bdc3c7; }}

@media (max-width: 768px) {{
  .tabs-wrapper {{ flex-direction: column; align-items: stretch; }}
  .tabs {{ flex-wrap: wrap; }}
  .search-box {{ width: 100%; }}
  .card-header {{ flex-wrap: wrap; }}
  .card-left {{ min-width: auto; }}
}}
</style>
</head>
<body>
<div class="container">

<div class="header">
  <h1>Wstatus {escape(report_title)} 报告</h1>
  <div class="date">日期: {escape(report_date)}</div>
</div>

<div class="summary">
  <div class="summary-card total">
    <div class="num">{total}</div>
    <div class="label">总分析</div>
  </div>
  <div class="summary-card pass">
    <div class="num">{len(core)}</div>
    <div class="label">核心</div>
  </div>
  <div class="summary-card watch">
    <div class="num">{len(watch)}</div>
    <div class="label">关注</div>
  </div>
  <div class="summary-card fail">
    <div class="num">{len(excluded)}</div>
    <div class="label">排除</div>
  </div>
  {not_confirmed_card}
</div>

<div class="tabs-wrapper">
  <div class="tabs">
    {tabs_html}
  </div>
  <div class="search-box">
    <span class="search-icon">&#128269;</span>
    <input type="text" class="search-input" placeholder="搜索股票名/代码..." autocomplete="off"
           oninput="searchStock(this.value)" onfocus="searchStock(this.value)" />
    <button class="search-clear" onclick="clearSearch()">&times;</button>
    <div class="search-dropdown" id="searchDropdown"></div>
  </div>
</div>

{tab_panes_html}

<div class="footer">
  免责声明：本报告仅供参考，不构成投资建议<br>
  Generated by wstatus · {escape(report_date)}
</div>

</div>

<script>
var _stockIndex = {{}};

(function buildIndex() {{
    var tabNames = {{
        "{tab_prefix}-core": "核心",
        "{tab_prefix}-watch": "关注",
        "{tab_prefix}-excluded": "排除",
        "{tab_prefix}-not_confirmed": "未确认"
    }};
    var tabClasses = {{
        "{tab_prefix}-core": "passed",
        "{tab_prefix}-watch": "watch",
        "{tab_prefix}-excluded": "fail",
        "{tab_prefix}-not_confirmed": "pending"
    }};
{search_entries}
    // Attach tab info to each entry
    Object.keys(_stockIndex).forEach(function(code) {{
        var entry = _stockIndex[code];
        entry.tabName = tabNames[entry.tabId] || entry.tabId;
        entry.tabClass = tabClasses[entry.tabId] || "";
    }});
}})();

function switchTab(tabId) {{
    document.querySelectorAll('.tab-btn').forEach(function(b) {{ b.classList.remove('active'); }});
    document.querySelectorAll('.tab-content').forEach(function(c) {{ c.classList.remove('active'); }});
    var targetTab = document.getElementById(tabId);
    if (targetTab) targetTab.classList.add('active');
    // Activate corresponding button
    var btns = document.querySelectorAll('.tab-btn');
    btns.forEach(function(b) {{
        if (b.textContent.trim().startsWith(tabId.replace('{tab_prefix}-', ''))) {{
            // match by group name prefix
        }}
    }});
    // Find button by matching tabId
    var tabMap = {{
        "{tab_prefix}-core": 0,
        "{tab_prefix}-watch": 1,
        "{tab_prefix}-excluded": {excluded_tab_idx},
        "{tab_prefix}-not_confirmed": 2
    }};
    var idx = tabMap[tabId];
    if (idx !== undefined && btns[idx]) btns[idx].classList.add('active');
}}

function toggleCard(header) {{
    var body = header.nextElementSibling;
    if (!body || !body.classList.contains('card-body')) {{
        // Try next sibling after skipping text nodes
        var next = header.nextSibling;
        while (next && next.nodeType !== 1) next = next.nextSibling;
        if (next && next.classList.contains('card-body')) body = next;
    }}
    if (!body) return;
    var isOpen = body.classList.contains('open');
    if (isOpen) {{
        body.classList.remove('open');
        header.classList.remove('expanded');
    }} else {{
        body.classList.add('open');
        header.classList.add('expanded');
    }}
}}

function toggleGroup(header) {{
    var body = header.nextElementSibling;
    if (!body || !body.classList.contains('group-body')) {{
        var next = header.nextSibling;
        while (next && next.nodeType !== 1) next = next.nextSibling;
        if (next && next.classList.contains('group-body')) body = next;
    }}
    if (!body) return;
    var isOpen = body.classList.contains('open');
    if (isOpen) {{
        body.classList.remove('open');
        header.classList.remove('expanded');
    }} else {{
        body.classList.add('open');
        header.classList.add('expanded');
    }}
}}

// ── Search ─────────────────────────────────────────
function searchStock(query) {{
    var dropdown = document.getElementById('searchDropdown');
    var clearBtn = document.querySelector('.search-clear');
    var q = query.trim().toLowerCase();

    if (!q) {{
        dropdown.classList.remove('open');
        dropdown.innerHTML = '';
        if (clearBtn) clearBtn.classList.remove('visible');
        return;
    }}

    if (clearBtn) clearBtn.classList.add('visible');

    var results = [];
    Object.keys(_stockIndex).forEach(function(code) {{
        var item = _stockIndex[code];
        if (item.symbol.toLowerCase().indexOf(q) !== -1 ||
            item.name.toLowerCase().indexOf(q) !== -1) {{
            results.push(item);
        }}
    }});

    results.sort(function(a, b) {{
        var aCode = a.symbol.toLowerCase();
        var bCode = b.symbol.toLowerCase();
        var aName = a.name.toLowerCase();
        var bName = b.name.toLowerCase();
        var aExact = (aCode === q || aName === q) ? 0 : 1;
        var bExact = (bCode === q || bName === q) ? 0 : 1;
        if (aExact !== bExact) return aExact - bExact;
        var aPrefix = (aCode.startsWith(q) || aName.startsWith(q)) ? 0 : 1;
        var bPrefix = (bCode.startsWith(q) || bName.startsWith(q)) ? 0 : 1;
        return aPrefix - bPrefix;
    }});

    if (results.length === 0) {{
        dropdown.innerHTML = '<div class="search-no-result">无匹配结果</div>';
    }} else {{
        dropdown.innerHTML = results.map(function(r) {{
            return '<div class="search-item" onclick="locateStock(\\'' + r.symbol + '\\', \\'' + r.tabId + '\\')">' +
                   '<span class="s-symbol">' + r.symbol + '</span>' +
                   '<span class="s-name">' + r.name + '</span>' +
                   '<span class="s-tab ' + r.tabClass + '">' + r.tabName + '</span>' +
                   '</div>';
        }}).join('');
    }}
    dropdown.classList.add('open');
}}

function locateStock(symbol, tabId) {{
    var dropdown = document.getElementById('searchDropdown');
    dropdown.classList.remove('open');
    var input = document.querySelector('.search-input');
    if (input) input.blur();

    switchTab(tabId);

    var card = document.getElementById('card_' + tabId.replace('{tab_prefix}-', '') + '_' + symbol);
    // Also try other prefixes
    if (!card) card = document.getElementById('card_c_' + symbol);
    if (!card) card = document.getElementById('card_w_' + symbol);
    if (!card) card = document.getElementById('card_e_' + symbol);
    if (!card) card = document.getElementById('card_n_' + symbol);

    if (!card) return;

    // Expand parent group if any
    var groupBody = card.closest('.group-body');
    if (groupBody) {{
        groupBody.classList.add('open');
        var groupHeader = groupBody.previousElementSibling;
        if (groupHeader) groupHeader.classList.add('expanded');
    }}

    // Expand card
    var header = card.querySelector('.card-header');
    var body = card.querySelector('.card-body');
    if (header && body && !body.classList.contains('open')) {{
        body.classList.add('open');
        header.classList.add('expanded');
    }}

    card.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    card.classList.add('highlight');
    setTimeout(function() {{ card.classList.remove('highlight'); }}, 1600);
}}

function clearSearch() {{
    var input = document.querySelector('.search-input');
    if (input) input.value = '';
    var dropdown = document.getElementById('searchDropdown');
    dropdown.classList.remove('open');
    dropdown.innerHTML = '';
    var clearBtn = document.querySelector('.search-clear');
    if (clearBtn) clearBtn.classList.remove('visible');
    if (input) input.focus();
}}

document.addEventListener('click', function(e) {{
    var box = document.querySelector('.search-box');
    var dropdown = document.getElementById('searchDropdown');
    if (box && dropdown && !box.contains(e.target)) {{
        dropdown.classList.remove('open');
    }}
}});
</script>
</body>
</html>'''


def _build_excluded_groups_html(groups: dict[str, list[dict[str, Any]]]) -> str:
    if not groups:
        return '<div class="empty-tab">无排除标的</div>'

    parts = []
    for idx, (cat_name, stocks) in enumerate(groups.items()):
        cn = _CN_NUM[idx] if idx < len(_CN_NUM) else str(idx + 1)
        cards = "\n".join(
            _build_card(r, prefix="e", show_rank=False) for r in stocks
        )
        parts.append(f'''
        <div class="excluded-group">
          <div class="group-header" onclick="toggleGroup(this)">
            <span class="group-title">{cn}、{escape(cat_name)}</span>
            <span class="group-count">{len(stocks)}只</span>
            <span class="expand-icon">▸</span>
          </div>
          <div class="group-body">
            {cards}
          </div>
        </div>''')
    return "\n".join(parts)


def export_html_report(
    results: list[dict[str, Any]], report_type: str, report_date: str, export_dir: str | Path
) -> str:
    output_dir = Path(export_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{report_type}_{report_date}.html"
    html = _build_html(results, report_type, report_date)
    path.write_text(html, encoding="utf-8")
    latest = output_dir / f"{report_type}_latest.html"
    latest.write_text(html, encoding="utf-8")
    return str(path)

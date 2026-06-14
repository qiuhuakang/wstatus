# Wstatus Dual-Mode Right-Side Screening Design

Date: 2026-06-14
Project: `wstatus`
Reference project: `D:\quant`

## Summary

Build a new Python stock-screening project in `D:\wstatus`, using `D:\quant` only as a reference for project shape and workflow. The new project keeps the proven daily pipeline style from `quant`: akshare data fetching, SQLite persistence, CLI entry points, CSV/HTML reports, and scheduled runs. The trading logic is replaced with two new right-side strategies:

- Mode A: chip-consolidation right-side setup.
- Mode B: crash-opportunity pit setup.

The v1 system runs twice per trading day:

- 20:00 Beijing time: daily stable screening from daily K-line data and the manual catalyst pool.
- 14:30 Beijing time: intraday snapshot confirmation and local report generation.

The output is layered into core selections and a watchlist. v1 generates local console, CSV, and HTML reports only. It does not send notifications, scrape news, or analyze intraday minute-level paths.

## Goals

- Create an independent `wstatus` project under `D:\wstatus`.
- Preserve the practical engineering shape of `D:\quant` without modifying it.
- Implement two strategy modes with shared data, scoring, reporting, and persistence.
- Support a stable daily screening run and a lighter 14:30 snapshot confirmation run.
- Use a manual catalyst pool for Mode B in v1.
- Keep the first version simple enough to verify with unit tests and real daily runs.

## Non-Goals

- Do not modify `D:\quant`.
- Do not build a generic trading-platform framework in v1.
- Do not add automatic announcement or news scraping in v1.
- Do not implement 1-minute or 5-minute intraday path recognition in v1.
- Do not add WeChat, Telegram, webhook, sound, or desktop push notifications in v1.
- Do not produce deterministic investment advice or position sizing instructions.

## Chosen Approach

Use the `quant` engineering skeleton as a reference, then rewrite the strategy core for `wstatus`.

This approach wins because it keeps the parts that are already useful: CLI flow, akshare integration, SQLite cache, reporting, and scheduled-script conventions. It avoids over-building a generic strategy plugin framework before the first usable version exists. It also avoids a throwaway one-script prototype that would make later reporting, caching, manual catalyst handling, and intraday confirmation messy.

## Repository Structure

```text
D:\wstatus
  main.py
  run_daily.py
  run_intraday.py
  requirements.txt
  config/
    settings.yaml
  src/
    __init__.py
    data_fetcher.py
    storage.py
    candidate_pool.py
    strategy_a.py
    strategy_b.py
    intraday_confirm.py
    scorer.py
    reporter.py
    html_reporter.py
    concurrency.py
  data/
    manual/
      catalyst_pool.csv
    export/
  db/
    main.db
  tests/
    test_strategy_a.py
    test_strategy_b.py
    test_intraday_confirm.py
    test_storage.py
```

## Runtime Modes

### Daily Screening at 20:00

The daily run produces the next trading session's confirmation pool.

1. Resolve the target trading day. If run on a non-trading day, use the most recent trading day.
2. Fetch or load the trading calendar and daily K-line data.
3. Build Mode A candidates from recent high-visibility and strong-trend stocks.
4. Build Mode B candidates from `data/manual/catalyst_pool.csv`.
5. Run `strategy_a` and `strategy_b`.
6. Score results and split them into `core`, `watch`, and `excluded`.
7. Save results and pending confirmation records to SQLite.
8. Export console, CSV, and HTML reports.

### Intraday Confirmation at 14:30

The intraday run checks the most recent pending confirmation pool.

1. Resolve today's trading session and load the latest pending confirmation records.
2. Fetch real-time stock snapshots.
3. Apply Mode A snapshot confirmation rules.
4. Apply Mode B snapshot confirmation rules.
5. Split results into `confirmed_core`, `confirmed_watch`, and `not_confirmed`.
6. Save confirmation results.
7. Export console, CSV, and HTML reports.

v1 uses real-time snapshots only. It approximates intraday behavior such as "small pullback then quick lift" through current price, change percentage, volume signals, and relationship to signal-day levels. Minute-level path recognition is reserved for a later version.

## Mode A: Chip-Consolidation Right-Side Setup

Mode A targets a classic right-side setup:

```text
Prior high with height and visibility
  -> right-side chip consolidation through sideways movement or mild pullback
  -> net-buying bullish doji signal day
  -> next-day small pullback and quick lift
  -> buy near the afternoon close
```

### Daily Candidate Sources

Mode A uses a mixed visibility model:

- Limit-up, two-board, multi-board, or large bullish candle events are preferred.
- Non-limit-up stocks can enter the watchlist if recent rise, turnover, and amount indicate a strong recognizable trend.

### Core Daily Conditions

A Mode A core candidate should satisfy:

- Recent prior high has meaningful height and visibility.
- Consolidation after the prior high lasts within the configured range.
- Pullback is mild and does not break the key consolidation low.
- Volatility contracts or stays controlled during consolidation.
- Volume does not show obvious distribution.
- The latest daily candle is a bullish doji-like signal day.
- The signal day shows better buying behavior than the preceding consolidation days.

### Watchlist Daily Conditions

A Mode A watch candidate may have:

- Strong trend and liquidity but no limit-up event.
- Consolidation close to valid but not clean enough for core.
- A signal day that is directionally useful but not textbook.
- One or two non-critical weaknesses while the price structure remains intact.

### 14:30 Confirmation

Mode A confirmation checks:

- The current price has repaired a weak open or is not meaningfully below the signal-day close.
- The current price is near or above the consolidation upper boundary.
- Snapshot volume or amount suggests money is returning.
- The setup has not broken the signal-day or consolidation risk line.

The report should label the reason as a snapshot approximation, not as full minute-level proof of "small pullback then quick lift."

## Mode B: Crash-Opportunity Pit Setup

Mode B targets an advanced right-side setup:

```text
Clear bullish catalyst first
  -> continuous sharp drop from reversible causes
  -> shrinking-volume doji within two trading days
  -> next day does not break signal-day low and turns bullish
  -> buy near the afternoon close
```

### Manual Catalyst Pool

Mode B v1 depends on a manually maintained CSV:

```csv
symbol,name,catalyst_date,catalyst_type,catalyst_summary,drop_reason,drop_reason_reversible,valid_until,notes
300000,示例股份,2026-06-12,订单/业绩/并购,签订重大合同,板块连坐,true,2026-06-25,人工确认利好仍有效
```

Required fields:

- `symbol`
- `name`
- `catalyst_date`
- `catalyst_type`
- `catalyst_summary`
- `drop_reason`
- `drop_reason_reversible`
- `valid_until`

Rows with missing required fields, invalid dates, expired catalysts, or `drop_reason_reversible` not set to true are skipped and reported as input issues.

### Core Daily Conditions

A Mode B core candidate should satisfy:

- The catalyst is present in the manual pool and still valid.
- The catalyst predates the crash.
- The drop reason is marked reversible, such as reduction-plan panic, sentiment selling, or sector drag.
- A sharp drop appears after the catalyst within the configured window.
- A shrinking-volume doji appears within two trading days after the sharp drop.
- The signal-day low is clear enough to serve as the risk line.

### Watchlist Daily Conditions

A Mode B watch candidate may have:

- A valid catalyst but weaker manual confidence.
- A drop that is severe enough directionally but not fully textbook.
- A doji that appears slightly late or with only partial volume shrinkage.
- Early repair behavior without a full confirmation condition.

### 14:30 Confirmation

Mode B confirmation checks:

- The current price is not below the signal-day low.
- The current snapshot suggests a bullish day or at least a strong repair toward positive territory.
- Volume does not imply a renewed panic extension.
- The confirmation report marks the candidate as "afternoon close buy observation" only when the risk line remains intact.

## Scoring and Grouping

Each strategy returns a structured analysis result. The scorer converts it into:

- `core`: structure, signal, and risk line are all sufficiently valid.
- `watch`: the setup is close but has defined weaknesses.
- `excluded`: the setup failed and should show explicit failure reasons.

Shared output fields:

- `symbol`
- `name`
- `mode`
- `group`
- `score`
- `signal_date`
- `confirm_date`
- `risk_price`
- `buy_observation_price`
- `reasons`
- `fail_reasons`

Mode A fields:

- `prior_high_date`
- `prior_high_price`
- `prior_high_rise_pct`
- `visibility_source`
- `consolidation_days`
- `consolidation_pullback_pct`
- `consolidation_low`
- `signal_doji_quality`
- `money_return_estimate`

Mode B fields:

- `catalyst_date`
- `catalyst_type`
- `catalyst_summary`
- `drop_reason`
- `drop_pct`
- `crash_days`
- `shrink_doji_date`
- `signal_low`

14:30 fields:

- `snapshot_time`
- `last_price`
- `pct_chg`
- `amount`
- `volume_ratio`
- `confirmed`
- `confirmation_group`
- `confirmation_reasons`
- `confirmation_fail_reasons`

## Persistence Design

SQLite should store:

- Daily K-line cache.
- Manual catalyst import issues.
- Daily screening results.
- Pending confirmation records.
- Intraday snapshot confirmation results.

The schema can evolve from the `quant` storage style, but names should reflect the new domain:

- `stock_daily`
- `daily_screen_result`
- `pending_confirmation`
- `intraday_confirm_result`
- `catalyst_import_issue`

## Data Sources

v1 uses akshare:

- Trading calendar from akshare.
- Daily K-line data, preferably forward-adjusted, matching the `quant` convention.
- Real-time stock snapshots for the 14:30 run.
- Limit-up pool or related market data only as an input to Mode A visibility, not as the whole strategy.

If a data fetch fails, the affected symbol should be marked with a failure reason and the batch should continue.

## Default Parameters

Initial defaults:

- Mode A prior-high visibility window: 60 trading days.
- Mode A consolidation length: 3 to 15 trading days.
- Mode A maximum mild pullback: 18% from the prior high.
- Mode A bullish doji: close above open, small body relative to range, non-extreme amplitude.
- Mode B catalyst validity: controlled by `valid_until`.
- Mode B crash window: 1 to 5 trading days after catalyst.
- Mode B shrinking-volume doji timing: within 2 trading days after the sharp drop.
- Mode B shrinking volume: signal-day volume below crash-period average volume.
- Core grouping: key structure, signal, and risk line pass.
- Watch grouping: one or two non-critical gaps are allowed.

These defaults should live in `config/settings.yaml` and be overridable by CLI arguments where useful.

## Error Handling

- Non-trading day daily run: use the most recent trading day.
- Non-trading day intraday run: print and report that no confirmation is available.
- Daily K-line fetch failure: skip the symbol and report the fetch failure.
- Real-time snapshot failure: retain the daily candidate but mark it as not confirmable.
- Catalyst CSV missing: run Mode A only and report that Mode B was skipped.
- Catalyst CSV row error: skip the row and export an import-issue report.
- Empty result set: still generate a report explaining that no candidates matched.

## Testing Strategy

Use small constructed pandas DataFrames for deterministic tests.

Tests should cover:

- Mode A bullish doji detection.
- Mode A prior-high and consolidation detection.
- Mode A core versus watch grouping.
- Mode B catalyst row validation.
- Mode B crash-window detection.
- Mode B shrinking-volume doji detection.
- Mode B signal-low risk-line behavior.
- 14:30 snapshot confirmation for both modes.
- SQLite table creation, pending confirmation write/read, and result persistence.
- CSV/HTML report generation with expected key fields.

The first implementation should be verifiable with commands shaped like:

```bash
python main.py --mode daily --date YYYY-MM-DD
python main.py --mode intraday --date YYYY-MM-DD
pytest
```

## Open Risks and Deferred Work

- Snapshot confirmation cannot prove intraday path behavior. This is accepted for v1 and should be labeled clearly in reports.
- Mode B depends on manual catalyst quality. Automation is explicitly deferred.
- akshare data availability and rate limits may affect runs. The pipeline should continue symbol by symbol.
- The exact numeric thresholds may need calibration after several real trading days.
- HTML report polish can follow once the data fields and grouping are stable.

## Acceptance Criteria

The design is ready for implementation planning when:

- The project is initialized independently in `D:\wstatus`.
- `D:\quant` remains untouched.
- Daily and intraday responsibilities are separate and clear.
- Mode A and Mode B have explicit v1 conditions.
- The manual catalyst pool format is specified.
- Reports, persistence, error handling, and tests have enough detail to plan implementation.

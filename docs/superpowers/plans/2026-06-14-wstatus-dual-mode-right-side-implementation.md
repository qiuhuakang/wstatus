# Wstatus Dual-Mode Right-Side Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use $superpower-subagents (recommended) or $superpower-executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking via update_plan.

**Goal:** Build the first usable `wstatus` Python project with daily Mode A/Mode B screening, 14:30 snapshot confirmation, SQLite persistence, and local CSV/HTML reports.

**Architecture:** Create a small Python CLI application modeled after `D:\quant`'s pipeline shape while keeping the strategy logic independent and portable to Linux. The code is split into focused modules: configuration, shared data contracts, strategy analyzers, confirmation, storage, data fetching, reporting, and pipeline orchestration. Tests use constructed pandas DataFrames and temporary SQLite databases so the strategy and persistence behavior is deterministic before real akshare data is used.

**Tech Stack:** Python 3.10+, pandas, numpy, akshare, PyYAML, pytest, SQLite, standard-library argparse/csv/json/html.

---

## Scope And File Map

Create these files:

- `requirements.txt`: runtime and test dependencies.
- `.gitignore`: generated data, caches, virtualenvs, and Python artifacts.
- `pytest.ini`: cross-platform pytest import path configuration.
- `config/settings.yaml`: default thresholds and paths.
- `main.py`: CLI entry point for `daily`, `intraday`, and `analyze`.
- `run_daily.py`: scheduler-friendly 20:00 daily run wrapper.
- `run_intraday.py`: scheduler-friendly 14:30 confirmation wrapper.
- `src/__init__.py`: package marker.
- `src/config.py`: load and normalize settings.
- `src/models.py`: shared dataclasses and dictionary conversion helpers.
- `src/strategy_common.py`: reusable candle, volume, date, and grouping helpers.
- `src/strategy_a.py`: Mode A chip-consolidation analysis.
- `src/strategy_b.py`: Mode B catalyst/crash/doji analysis and catalyst CSV validation.
- `src/intraday_confirm.py`: Mode A and Mode B snapshot confirmation.
- `src/scorer.py`: deterministic scoring and `core`/`watch`/`excluded` grouping.
- `src/storage.py`: SQLite schema and CRUD for daily results and pending confirmations.
- `src/data_fetcher.py`: akshare wrappers and test-friendly interfaces.
- `src/candidate_pool.py`: Mode A and Mode B candidate construction.
- `src/reporter.py`: console and CSV reports.
- `src/html_reporter.py`: simple local HTML report.
- `src/pipeline.py`: daily and intraday orchestration.
- `src/concurrency.py`: small rate limiter and fetch helper, adapted from `D:\quant`.
- `data/manual/catalyst_pool.csv`: empty-but-valid manual catalyst pool template.
- `tests/conftest.py`: reusable fixtures.
- `tests/test_strategy_common.py`: shared helper tests.
- `tests/test_strategy_a.py`: Mode A tests.
- `tests/test_strategy_b.py`: Mode B tests.
- `tests/test_intraday_confirm.py`: 14:30 snapshot tests.
- `tests/test_storage.py`: SQLite tests.
- `tests/test_reporter.py`: report generation tests.
- `tests/test_pipeline.py`: orchestration tests with fake fetchers.

Do not modify `D:\quant`.

## Linux Compatibility Contract

The project must run on both Windows and Linux from the same repository:

- Use `pathlib.Path` and project-relative settings paths; never hardcode `D:\wstatus`, drive letters, or backslash-only path joins in runtime code.
- Open text files with explicit UTF-8 or UTF-8-SIG where CSV input may come from Excel.
- Keep CLI commands portable: `python main.py --mode daily ...`, `python main.py --mode intraday ...`, and `pytest ...`.
- Keep generated files under project-relative `db/` and `data/export/`, both ignored where appropriate.
- Linux scheduling should work through cron or systemd timers by calling `python /path/to/wstatus/main.py --mode daily` at 20:00 and `python /path/to/wstatus/main.py --mode intraday` at 14:30.
- Tests must not depend on Windows-only absolute paths. When checking the root path, assert repository shape rather than a drive-specific prefix.

## Shared Data Contracts

Use these dictionary keys consistently across modules:

Daily analysis result:

```python
{
    "symbol": "000001",
    "name": "Ping An Bank",
    "mode": "A",
    "group": "core",
    "score": 86.0,
    "signal_date": "2026-06-12",
    "confirm_date": "",
    "risk_price": 10.25,
    "buy_observation_price": 10.92,
    "reasons": ["prior high is visible"],
    "fail_reasons": [],
}
```

Pending confirmation row:

```python
{
    "screen_date": "2026-06-12",
    "symbol": "000001",
    "name": "Ping An Bank",
    "mode": "A",
    "group": "core",
    "signal_date": "2026-06-12",
    "signal_low": 10.25,
    "signal_close": 10.80,
    "risk_price": 10.25,
    "upper_trigger_price": 10.95,
    "payload_json": "{}",
}
```

Snapshot row:

```python
{
    "symbol": "000001",
    "name": "Ping An Bank",
    "last_price": 10.98,
    "open": 10.70,
    "prev_close": 10.80,
    "high": 11.05,
    "low": 10.62,
    "pct_chg": 1.67,
    "amount": 180000000.0,
    "volume_ratio": 1.35,
    "snapshot_time": "2026-06-15 14:30:00",
}
```

---

### Task 1: Scaffold Project Configuration

**Files:**
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `pytest.ini`
- Create: `config/settings.yaml`
- Create: `src/__init__.py`
- Create: `src/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing configuration tests**

Create `tests/test_config.py`:

```python
from pathlib import Path

from src.config import get_project_root, load_settings


def test_get_project_root_points_at_repo_root():
    root = get_project_root()
    assert root.name == "wstatus"
    assert (root / "docs" / "superpowers").exists()


def test_load_settings_reads_thresholds_and_resolves_paths():
    settings = load_settings()
    assert settings["params"]["mode_a"]["prior_high_window"] == 60
    assert settings["params"]["mode_b"]["crash_window_days"] == 5
    assert Path(settings["paths"]["db"]).is_absolute()
    assert Path(settings["paths"]["export_dir"]).is_absolute()
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
pytest tests/test_config.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.config'`.

- [ ] **Step 3: Create dependency and ignore files**

Create `requirements.txt`:

```text
akshare>=1.14.0
pandas>=2.0.0
numpy>=1.24.0
PyYAML>=6.0.0
pytest>=8.0.0
```

Create `.gitignore`:

```text
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
venv/
env/
db/*.db
db/*.db-journal
data/export/
.superpowers/
```

Create `pytest.ini`:

```ini
[pytest]
pythonpath = .
```

Create `src/__init__.py`:

```python
"""Wstatus stock-screening package."""
```

- [ ] **Step 4: Create settings file**

Create `config/settings.yaml`:

```yaml
paths:
  db: db/main.db
  export_dir: data/export
  catalyst_pool: data/manual/catalyst_pool.csv

params:
  mode_a:
    prior_high_window: 60
    min_prior_rise_pct: 18.0
    min_amount: 100000000
    consolidation_min_days: 3
    consolidation_max_days: 15
    max_pullback_pct: 18.0
    max_signal_body_ratio: 0.35
    max_signal_amplitude_pct: 9.0
    volume_shrink_threshold: 1.10
    upper_trigger_buffer_pct: 1.0
  mode_b:
    crash_window_days: 5
    min_crash_pct: 14.0
    max_signal_body_ratio: 0.30
    max_signal_amplitude_pct: 10.0
    shrink_volume_ratio: 0.75
    signal_after_crash_days: 2
  intraday:
    repair_buffer_pct: -1.0
    amount_min_ratio: 0.80
    volume_ratio_min: 0.80
  scoring:
    core_min_score: 75
    watch_min_score: 55

runtime:
  calendar_days: 220
  max_workers: 8
  max_per_second: 8
```

- [ ] **Step 5: Implement settings loading**

Create `src/config.py`:

```python
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


DEFAULT_SETTINGS_PATH = Path("config/settings.yaml")


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_path(root: Path, value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str((root / path).resolve())


def load_settings(path: str | Path | None = None) -> dict[str, Any]:
    root = get_project_root()
    settings_path = Path(path) if path is not None else root / DEFAULT_SETTINGS_PATH
    with settings_path.open("r", encoding="utf-8") as f:
        settings = yaml.safe_load(f) or {}

    result = deepcopy(settings)
    paths = result.setdefault("paths", {})
    for key in ("db", "export_dir", "catalyst_pool"):
        if key in paths:
            paths[key] = _resolve_path(root, str(paths[key]))
    return result
```

- [ ] **Step 6: Run the configuration tests**

Run:

```bash
pytest tests/test_config.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add .gitignore pytest.ini requirements.txt config/settings.yaml src/__init__.py src/config.py tests/test_config.py
git commit -m "chore: scaffold project configuration"
```

---

### Task 2: Add Shared Models And Strategy Helpers

**Files:**
- Create: `src/models.py`
- Create: `src/strategy_common.py`
- Test: `tests/test_strategy_common.py`

- [ ] **Step 1: Write failing helper tests**

Create `tests/test_strategy_common.py`:

```python
import pandas as pd

from src.strategy_common import (
    calc_body_ratio,
    calc_pullback_pct,
    detect_bullish_doji,
    detect_shrinking_volume,
    normalize_daily_frame,
)


def test_detect_bullish_doji_accepts_small_green_body():
    row = {"open": 10.0, "high": 10.8, "low": 9.8, "close": 10.2, "volume": 1000}
    result = detect_bullish_doji(row, max_body_ratio=0.35, max_amplitude_pct=12.0)
    assert result["passed"] is True
    assert result["body_ratio"] == 0.2


def test_detect_bullish_doji_rejects_red_body():
    row = {"open": 10.3, "high": 10.8, "low": 9.8, "close": 10.1, "volume": 1000}
    result = detect_bullish_doji(row, max_body_ratio=0.35, max_amplitude_pct=12.0)
    assert result["passed"] is False
    assert "close_not_above_open" in result["fail_reasons"]


def test_detect_shrinking_volume_compares_signal_to_baseline():
    assert detect_shrinking_volume(signal_volume=600, baseline_volume=1000, threshold=0.75) is True
    assert detect_shrinking_volume(signal_volume=900, baseline_volume=1000, threshold=0.75) is False


def test_calc_pullback_pct_from_prior_high_to_low():
    assert calc_pullback_pct(prior_high=20.0, current_low=17.0) == 15.0


def test_normalize_daily_frame_sorts_and_adds_pct_change():
    df = pd.DataFrame(
        [
            {"trade_date": "2026-06-03", "open": 11, "high": 12, "low": 10, "close": 11, "volume": 100, "amount": 1000},
            {"trade_date": "2026-06-01", "open": 10, "high": 11, "low": 9, "close": 10, "volume": 100, "amount": 1000},
            {"trade_date": "2026-06-02", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 100, "amount": 1000},
        ]
    )
    normalized = normalize_daily_frame(df)
    assert normalized["trade_date"].tolist() == ["2026-06-01", "2026-06-02", "2026-06-03"]
    assert normalized["pct_chg"].round(2).tolist() == [0.0, 5.0, 4.76]
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
pytest tests/test_strategy_common.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.strategy_common'`.

- [ ] **Step 3: Implement shared dataclasses**

Create `src/models.py`:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class AnalysisResult:
    symbol: str
    name: str
    mode: str
    group: str
    score: float
    signal_date: str
    confirm_date: str = ""
    risk_price: float = 0.0
    buy_observation_price: float = 0.0
    reasons: list[str] = field(default_factory=list)
    fail_reasons: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        extra = data.pop("extra")
        data.update(extra)
        return data


@dataclass
class PendingConfirmation:
    screen_date: str
    symbol: str
    name: str
    mode: str
    group: str
    signal_date: str
    signal_low: float
    signal_close: float
    risk_price: float
    upper_trigger_price: float
    payload_json: str = "{}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Snapshot:
    symbol: str
    name: str
    last_price: float
    open: float
    prev_close: float
    high: float
    low: float
    pct_chg: float
    amount: float
    volume_ratio: float
    snapshot_time: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
```

- [ ] **Step 4: Implement strategy helpers**

Create `src/strategy_common.py`:

```python
from __future__ import annotations

from typing import Mapping

import pandas as pd


REQUIRED_DAILY_COLUMNS = ["trade_date", "open", "high", "low", "close", "volume", "amount"]


def normalize_daily_frame(df: pd.DataFrame) -> pd.DataFrame:
    missing = [col for col in REQUIRED_DAILY_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"daily frame missing columns: {missing}")
    result = df.copy()
    result["trade_date"] = result["trade_date"].astype(str)
    result = result.sort_values("trade_date").reset_index(drop=True)
    result["pct_chg"] = result["close"].pct_change().fillna(0.0) * 100
    result["amplitude"] = ((result["high"] - result["low"]) / result["close"].shift(1)).fillna(0.0) * 100
    return result


def calc_body_ratio(row: Mapping[str, float]) -> float:
    high = float(row["high"])
    low = float(row["low"])
    if high <= low:
        return 1.0
    body = abs(float(row["close"]) - float(row["open"]))
    return round(body / (high - low), 3)


def calc_amplitude_pct(row: Mapping[str, float]) -> float:
    close = float(row["close"])
    if close <= 0:
        return 0.0
    return round((float(row["high"]) - float(row["low"])) / close * 100, 2)


def calc_pullback_pct(prior_high: float, current_low: float) -> float:
    if prior_high <= 0:
        return 0.0
    return round((prior_high - current_low) / prior_high * 100, 2)


def detect_bullish_doji(
    row: Mapping[str, float],
    max_body_ratio: float,
    max_amplitude_pct: float,
) -> dict:
    fail_reasons: list[str] = []
    if float(row["close"]) <= float(row["open"]):
        fail_reasons.append("close_not_above_open")
    body_ratio = calc_body_ratio(row)
    if body_ratio > max_body_ratio:
        fail_reasons.append("body_too_large")
    amplitude_pct = calc_amplitude_pct(row)
    if amplitude_pct > max_amplitude_pct:
        fail_reasons.append("amplitude_too_large")
    return {
        "passed": len(fail_reasons) == 0,
        "body_ratio": body_ratio,
        "amplitude_pct": amplitude_pct,
        "fail_reasons": fail_reasons,
    }


def detect_shrinking_volume(signal_volume: float, baseline_volume: float, threshold: float) -> bool:
    if baseline_volume <= 0:
        return False
    return signal_volume / baseline_volume <= threshold
```

- [ ] **Step 5: Run the helper tests**

Run:

```bash
pytest tests/test_strategy_common.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add src/models.py src/strategy_common.py tests/test_strategy_common.py
git commit -m "feat: add shared strategy helpers"
```

---

### Task 3: Implement Mode A Daily Strategy

**Files:**
- Create: `src/strategy_a.py`
- Test: `tests/test_strategy_a.py`

- [ ] **Step 1: Write failing Mode A tests**

Create `tests/test_strategy_a.py`:

```python
import pandas as pd

from src.strategy_a import analyze_mode_a


SETTINGS = {
    "prior_high_window": 60,
    "min_prior_rise_pct": 18.0,
    "min_amount": 100000000,
    "consolidation_min_days": 3,
    "consolidation_max_days": 15,
    "max_pullback_pct": 18.0,
    "max_signal_body_ratio": 0.35,
    "max_signal_amplitude_pct": 9.0,
    "volume_shrink_threshold": 1.10,
    "upper_trigger_buffer_pct": 1.0,
}


def mode_a_frame(signal_close=18.2, signal_open=18.0, signal_low=17.7):
    rows = []
    close = 10.0
    for i in range(20):
        rows.append({"trade_date": f"2026-05-{i+1:02d}", "open": close, "high": close + 0.4, "low": close - 0.2, "close": close + 0.2, "volume": 800, "amount": 90000000})
        close += 0.2
    rows.append({"trade_date": "2026-05-21", "open": 14.0, "high": 18.8, "low": 13.8, "close": 18.0, "volume": 3000, "amount": 250000000})
    for day, price, volume in [
        ("2026-05-22", 17.6, 1800),
        ("2026-05-25", 17.8, 1500),
        ("2026-05-26", 17.7, 1300),
        ("2026-05-27", 17.9, 1200),
    ]:
        rows.append({"trade_date": day, "open": price - 0.1, "high": price + 0.35, "low": price - 0.35, "close": price, "volume": volume, "amount": 160000000})
    rows.append({"trade_date": "2026-05-28", "open": signal_open, "high": 18.6, "low": signal_low, "close": signal_close, "volume": 1250, "amount": 180000000})
    return pd.DataFrame(rows)


def test_analyze_mode_a_returns_core_for_clean_chip_consolidation():
    result = analyze_mode_a("000001", "Alpha", mode_a_frame(), SETTINGS)
    assert result["group"] == "core"
    assert result["mode"] == "A"
    assert result["signal_date"] == "2026-05-28"
    assert result["risk_price"] == 17.55
    assert result["upper_trigger_price"] > result["signal_close"]
    assert "bullish_doji_signal" in result["reasons"]


def test_analyze_mode_a_returns_watch_for_non_limit_strong_trend():
    df = mode_a_frame()
    df.loc[df["trade_date"] == "2026-05-21", "high"] = 17.0
    df.loc[df["trade_date"] == "2026-05-21", "close"] = 16.5
    result = analyze_mode_a("000002", "Beta", df, SETTINGS)
    assert result["group"] == "watch"
    assert "visibility_weaker_than_core" in result["fail_reasons"]


def test_analyze_mode_a_excludes_when_signal_breaks_consolidation_low():
    result = analyze_mode_a("000003", "Gamma", mode_a_frame(signal_low=16.0, signal_close=16.4, signal_open=16.2), SETTINGS)
    assert result["group"] == "excluded"
    assert "signal_breaks_consolidation_low" in result["fail_reasons"]
```

- [ ] **Step 2: Run the Mode A tests and verify they fail**

Run:

```bash
pytest tests/test_strategy_a.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.strategy_a'`.

- [ ] **Step 3: Implement Mode A**

Create `src/strategy_a.py`:

```python
from __future__ import annotations

import pandas as pd

from src.strategy_common import calc_pullback_pct, detect_bullish_doji, normalize_daily_frame


def _find_prior_high(df: pd.DataFrame, settings: dict) -> dict | None:
    if len(df) < settings["consolidation_min_days"] + 2:
        return None
    signal_idx = len(df) - 1
    search_start = max(0, signal_idx - settings["prior_high_window"])
    search_end = signal_idx - settings["consolidation_min_days"]
    if search_end <= search_start:
        return None
    segment = df.iloc[search_start:search_end + 1]
    idx = int(segment["high"].idxmax())
    high_row = df.loc[idx]
    pre_start = max(0, idx - 20)
    base_close = float(df.iloc[pre_start]["close"])
    rise_pct = round((float(high_row["high"]) - base_close) / base_close * 100, 2) if base_close > 0 else 0.0
    high_to_close_pct = round((float(high_row["close"]) - float(high_row["open"])) / float(high_row["open"]) * 100, 2) if float(high_row["open"]) > 0 else 0.0
    visibility_source = "limit_or_large_bullish" if high_to_close_pct >= 9.0 else "strong_trend"
    return {
        "idx": idx,
        "date": str(high_row["trade_date"]),
        "price": round(float(high_row["high"]), 2),
        "rise_pct": rise_pct,
        "visibility_source": visibility_source,
    }


def _score_mode_a(passed: list[str], soft_fails: list[str], hard_fails: list[str]) -> tuple[str, float]:
    score = 40.0 + len(passed) * 8.0 - len(soft_fails) * 8.0 - len(hard_fails) * 20.0
    score = max(0.0, min(100.0, score))
    if hard_fails:
        return "excluded", round(score, 1)
    if score >= 75 and not soft_fails:
        return "core", round(score, 1)
    if score >= 55:
        return "watch", round(score, 1)
    return "excluded", round(score, 1)


def analyze_mode_a(symbol: str, name: str, daily_df: pd.DataFrame, settings: dict) -> dict:
    df = normalize_daily_frame(daily_df)
    reasons: list[str] = []
    soft_fails: list[str] = []
    hard_fails: list[str] = []

    prior = _find_prior_high(df, settings)
    if prior is None:
        return {
            "symbol": symbol,
            "name": name,
            "mode": "A",
            "group": "excluded",
            "score": 0.0,
            "signal_date": "",
            "risk_price": 0.0,
            "buy_observation_price": 0.0,
            "reasons": [],
            "fail_reasons": ["prior_high_not_found"],
        }

    signal = df.iloc[-1]
    consolidation = df.iloc[prior["idx"] + 1:]
    consolidation_days = len(consolidation)
    consolidation_low = round(float(consolidation["low"].min()), 2)
    pullback_pct = calc_pullback_pct(prior["price"], consolidation_low)
    signal_check = detect_bullish_doji(
        signal,
        max_body_ratio=settings["max_signal_body_ratio"],
        max_amplitude_pct=settings["max_signal_amplitude_pct"],
    )
    avg_consolidation_volume = float(consolidation.iloc[:-1]["volume"].mean()) if len(consolidation) > 1 else float(signal["volume"])
    volume_ok = float(signal["volume"]) <= avg_consolidation_volume * settings["volume_shrink_threshold"]

    if prior["rise_pct"] >= settings["min_prior_rise_pct"]:
        reasons.append("prior_high_has_height")
    else:
        soft_fails.append("prior_high_height_weak")

    if prior["visibility_source"] == "limit_or_large_bullish":
        reasons.append("high_visibility_event")
    else:
        soft_fails.append("visibility_weaker_than_core")

    if settings["consolidation_min_days"] <= consolidation_days <= settings["consolidation_max_days"]:
        reasons.append("consolidation_days_valid")
    else:
        hard_fails.append("consolidation_days_out_of_range")

    if pullback_pct <= settings["max_pullback_pct"]:
        reasons.append("pullback_controlled")
    else:
        hard_fails.append("pullback_too_deep")

    if signal_check["passed"]:
        reasons.append("bullish_doji_signal")
    else:
        hard_fails.extend(signal_check["fail_reasons"])

    prior_consolidation_low = round(float(consolidation.iloc[:-1]["low"].min()), 2) if len(consolidation) > 1 else consolidation_low
    if float(signal["low"]) < prior_consolidation_low:
        hard_fails.append("signal_breaks_consolidation_low")

    if volume_ok:
        reasons.append("volume_not_distributing")
    else:
        soft_fails.append("signal_volume_too_large")

    group, score = _score_mode_a(reasons, soft_fails, hard_fails)
    upper_trigger_price = round(float(consolidation["high"].max()) * (1 + settings["upper_trigger_buffer_pct"] / 100), 2)
    signal_close = round(float(signal["close"]), 2)
    result = {
        "symbol": symbol,
        "name": name,
        "mode": "A",
        "group": group,
        "score": score,
        "signal_date": str(signal["trade_date"]),
        "confirm_date": "",
        "risk_price": prior_consolidation_low,
        "buy_observation_price": signal_close,
        "reasons": reasons,
        "fail_reasons": soft_fails + hard_fails,
        "prior_high_date": prior["date"],
        "prior_high_price": prior["price"],
        "prior_high_rise_pct": prior["rise_pct"],
        "visibility_source": prior["visibility_source"],
        "consolidation_days": consolidation_days,
        "consolidation_pullback_pct": pullback_pct,
        "consolidation_low": consolidation_low,
        "signal_doji_quality": signal_check["body_ratio"],
        "money_return_estimate": "snapshot_required",
        "signal_low": round(float(signal["low"]), 2),
        "signal_close": signal_close,
        "upper_trigger_price": upper_trigger_price,
    }
    return result
```

- [ ] **Step 4: Run the Mode A tests**

Run:

```bash
pytest tests/test_strategy_a.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/strategy_a.py tests/test_strategy_a.py
git commit -m "feat: add mode a daily strategy"
```

---

### Task 4: Implement Mode B Catalyst And Crash Strategy

**Files:**
- Create: `src/strategy_b.py`
- Create: `data/manual/catalyst_pool.csv`
- Test: `tests/test_strategy_b.py`

- [ ] **Step 1: Write failing Mode B tests**

Create `tests/test_strategy_b.py`:

```python
from pathlib import Path

import pandas as pd

from src.strategy_b import analyze_mode_b, load_catalyst_pool


SETTINGS = {
    "crash_window_days": 5,
    "min_crash_pct": 14.0,
    "max_signal_body_ratio": 0.30,
    "max_signal_amplitude_pct": 10.0,
    "shrink_volume_ratio": 0.75,
    "signal_after_crash_days": 2,
}


def mode_b_frame(signal_close=8.35, signal_open=8.25, signal_low=8.05, signal_volume=900):
    return pd.DataFrame(
        [
            {"trade_date": "2026-06-10", "open": 10.0, "high": 10.5, "low": 9.8, "close": 10.4, "volume": 1000, "amount": 120000000},
            {"trade_date": "2026-06-11", "open": 10.4, "high": 10.6, "low": 9.3, "close": 9.4, "volume": 2400, "amount": 220000000},
            {"trade_date": "2026-06-12", "open": 9.2, "high": 9.3, "low": 8.1, "close": 8.2, "volume": 2600, "amount": 230000000},
            {"trade_date": "2026-06-15", "open": signal_open, "high": 8.55, "low": signal_low, "close": signal_close, "volume": signal_volume, "amount": 95000000},
        ]
    )


def catalyst():
    return {
        "symbol": "300000",
        "name": "Catalyst",
        "catalyst_date": "2026-06-10",
        "catalyst_type": "order",
        "catalyst_summary": "large contract",
        "drop_reason": "sector selloff",
        "drop_reason_reversible": True,
        "valid_until": "2026-06-25",
        "notes": "manual check",
    }


def test_load_catalyst_pool_accepts_valid_rows(tmp_path):
    path = tmp_path / "catalyst_pool.csv"
    path.write_text(
        "symbol,name,catalyst_date,catalyst_type,catalyst_summary,drop_reason,drop_reason_reversible,valid_until,notes\n"
        "300000,Catalyst,2026-06-10,order,large contract,sector selloff,true,2026-06-25,manual check\n",
        encoding="utf-8",
    )
    rows, issues = load_catalyst_pool(path, as_of_date="2026-06-14")
    assert len(rows) == 1
    assert issues == []
    assert rows[0]["drop_reason_reversible"] is True


def test_load_catalyst_pool_reports_expired_and_irreversible_rows(tmp_path):
    path = tmp_path / "catalyst_pool.csv"
    path.write_text(
        "symbol,name,catalyst_date,catalyst_type,catalyst_summary,drop_reason,drop_reason_reversible,valid_until,notes\n"
        "300001,Expired,2026-06-01,order,old,sector,false,2026-06-05,old row\n",
        encoding="utf-8",
    )
    rows, issues = load_catalyst_pool(path, as_of_date="2026-06-14")
    assert rows == []
    assert issues[0]["symbol"] == "300001"
    assert "drop_reason_not_reversible" in issues[0]["issue"]
    assert "catalyst_expired" in issues[0]["issue"]


def test_analyze_mode_b_returns_core_for_crash_and_shrinking_doji():
    result = analyze_mode_b(catalyst(), mode_b_frame(), SETTINGS)
    assert result["group"] == "core"
    assert result["mode"] == "B"
    assert result["signal_date"] == "2026-06-15"
    assert result["risk_price"] == 8.05
    assert "shrinking_volume_doji" in result["reasons"]


def test_analyze_mode_b_excludes_when_signal_volume_does_not_shrink():
    result = analyze_mode_b(catalyst(), mode_b_frame(signal_volume=2300), SETTINGS)
    assert result["group"] == "excluded"
    assert "signal_volume_not_shrinking" in result["fail_reasons"]
```

- [ ] **Step 2: Run the Mode B tests and verify they fail**

Run:

```bash
pytest tests/test_strategy_b.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.strategy_b'`.

- [ ] **Step 3: Create the manual catalyst pool template**

Create `data/manual/catalyst_pool.csv`:

```csv
symbol,name,catalyst_date,catalyst_type,catalyst_summary,drop_reason,drop_reason_reversible,valid_until,notes
```

- [ ] **Step 4: Implement Mode B**

Create `src/strategy_b.py`:

```python
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from src.strategy_common import detect_bullish_doji, detect_shrinking_volume, normalize_daily_frame


REQUIRED_CATALYST_FIELDS = [
    "symbol",
    "name",
    "catalyst_date",
    "catalyst_type",
    "catalyst_summary",
    "drop_reason",
    "drop_reason_reversible",
    "valid_until",
]


def _parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        return None


def load_catalyst_pool(path: str | Path, as_of_date: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    file_path = Path(path)
    if not file_path.exists():
        return [], [{"symbol": "", "issue": "catalyst_pool_missing", "row": {}}]

    as_of = date.fromisoformat(as_of_date)
    valid_rows: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []
    with file_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for line_no, row in enumerate(reader, start=2):
            issue_parts: list[str] = []
            missing = [field for field in REQUIRED_CATALYST_FIELDS if not row.get(field)]
            if missing:
                issue_parts.append("missing_" + "_".join(missing))

            catalyst_date = _parse_date(row.get("catalyst_date", ""))
            valid_until = _parse_date(row.get("valid_until", ""))
            if catalyst_date is None:
                issue_parts.append("invalid_catalyst_date")
            if valid_until is None:
                issue_parts.append("invalid_valid_until")
            elif valid_until < as_of:
                issue_parts.append("catalyst_expired")

            reversible = _parse_bool(row.get("drop_reason_reversible", ""))
            if not reversible:
                issue_parts.append("drop_reason_not_reversible")

            if issue_parts:
                issues.append({"symbol": row.get("symbol", ""), "line_no": line_no, "issue": ",".join(issue_parts), "row": dict(row)})
                continue

            normalized = dict(row)
            normalized["drop_reason_reversible"] = reversible
            valid_rows.append(normalized)
    return valid_rows, issues


def _score_mode_b(reasons: list[str], soft_fails: list[str], hard_fails: list[str]) -> tuple[str, float]:
    score = 45.0 + len(reasons) * 9.0 - len(soft_fails) * 8.0 - len(hard_fails) * 22.0
    score = max(0.0, min(100.0, score))
    if hard_fails:
        return "excluded", round(score, 1)
    if score >= 75 and not soft_fails:
        return "core", round(score, 1)
    if score >= 55:
        return "watch", round(score, 1)
    return "excluded", round(score, 1)


def analyze_mode_b(catalyst_row: dict[str, Any], daily_df: pd.DataFrame, settings: dict) -> dict:
    df = normalize_daily_frame(daily_df)
    catalyst_date = str(catalyst_row["catalyst_date"])
    after = df[df["trade_date"] >= catalyst_date].copy().reset_index(drop=True)
    reasons: list[str] = ["valid_manual_catalyst"]
    soft_fails: list[str] = []
    hard_fails: list[str] = []

    if len(after) < 3:
        hard_fails.append("not_enough_bars_after_catalyst")
        signal = df.iloc[-1]
        return {
            "symbol": catalyst_row["symbol"],
            "name": catalyst_row["name"],
            "mode": "B",
            "group": "excluded",
            "score": 0.0,
            "signal_date": str(signal["trade_date"]),
            "risk_price": round(float(signal["low"]), 2),
            "buy_observation_price": round(float(signal["close"]), 2),
            "reasons": reasons,
            "fail_reasons": hard_fails,
        }

    crash_window = after.iloc[: settings["crash_window_days"] + 1]
    start_close = float(crash_window.iloc[0]["close"])
    crash_low = float(crash_window["low"].min())
    drop_pct = round((start_close - crash_low) / start_close * 100, 2) if start_close > 0 else 0.0
    crash_low_idx = int(crash_window["low"].idxmin())
    signal_start = crash_low_idx + 1
    signal_end = min(len(after), signal_start + settings["signal_after_crash_days"])
    signal_candidates = after.iloc[signal_start:signal_end]

    if drop_pct >= settings["min_crash_pct"]:
        reasons.append("sharp_reversible_drop")
    else:
        hard_fails.append("crash_drop_too_small")

    best_signal = None
    for _, candidate in signal_candidates.iterrows():
        doji = detect_bullish_doji(
            candidate,
            max_body_ratio=settings["max_signal_body_ratio"],
            max_amplitude_pct=settings["max_signal_amplitude_pct"],
        )
        crash_volume = float(after.iloc[1 : crash_low_idx + 1]["volume"].mean()) if crash_low_idx >= 1 else float(after.iloc[0]["volume"])
        shrink = detect_shrinking_volume(float(candidate["volume"]), crash_volume, settings["shrink_volume_ratio"])
        if doji["passed"] and shrink:
            best_signal = (candidate, doji, crash_volume)
            break
        if doji["passed"] and not shrink:
            hard_fails.append("signal_volume_not_shrinking")

    if best_signal is None:
        if "signal_volume_not_shrinking" not in hard_fails:
            hard_fails.append("shrinking_doji_not_found")
        signal = after.iloc[-1]
        signal_quality = 1.0
    else:
        signal, doji, crash_volume = best_signal
        signal_quality = doji["body_ratio"]
        reasons.append("shrinking_volume_doji")

    group, score = _score_mode_b(reasons, soft_fails, hard_fails)
    signal_low = round(float(signal["low"]), 2)
    signal_close = round(float(signal["close"]), 2)
    return {
        "symbol": catalyst_row["symbol"],
        "name": catalyst_row["name"],
        "mode": "B",
        "group": group,
        "score": score,
        "signal_date": str(signal["trade_date"]),
        "confirm_date": "",
        "risk_price": signal_low,
        "buy_observation_price": signal_close,
        "reasons": reasons,
        "fail_reasons": soft_fails + hard_fails,
        "catalyst_date": catalyst_row["catalyst_date"],
        "catalyst_type": catalyst_row["catalyst_type"],
        "catalyst_summary": catalyst_row["catalyst_summary"],
        "drop_reason": catalyst_row["drop_reason"],
        "drop_pct": drop_pct,
        "crash_days": max(1, crash_low_idx),
        "shrink_doji_date": str(signal["trade_date"]) if best_signal is not None else "",
        "signal_low": signal_low,
        "signal_close": signal_close,
        "upper_trigger_price": signal_close,
        "signal_doji_quality": signal_quality,
    }
```

- [ ] **Step 5: Run the Mode B tests**

Run:

```bash
pytest tests/test_strategy_b.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add src/strategy_b.py data/manual/catalyst_pool.csv tests/test_strategy_b.py
git commit -m "feat: add mode b catalyst strategy"
```

---

### Task 5: Implement Intraday Snapshot Confirmation

**Files:**
- Create: `src/intraday_confirm.py`
- Test: `tests/test_intraday_confirm.py`

- [ ] **Step 1: Write failing confirmation tests**

Create `tests/test_intraday_confirm.py`:

```python
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
    assert "mode_a_trigger_reached" in result["confirmation_reasons"]


def test_reject_mode_a_when_risk_line_breaks():
    result = confirm_pending(pending("A"), snapshot(last_price=9.9, low=9.8, pct_chg=-8.0), SETTINGS)
    assert result["confirmed"] is False
    assert result["confirmation_group"] == "not_confirmed"
    assert "risk_line_broken" in result["confirmation_fail_reasons"]


def test_confirm_mode_b_when_signal_low_holds_and_price_repairs():
    p = pending("B")
    p["upper_trigger_price"] = 10.8
    result = confirm_pending(p, snapshot(last_price=10.9, low=10.1, pct_chg=0.93), SETTINGS)
    assert result["confirmed"] is True
    assert "mode_b_signal_low_held" in result["confirmation_reasons"]


def test_watch_confirmation_when_volume_is_weak():
    result = confirm_pending(pending("A"), snapshot(volume_ratio=0.4), SETTINGS)
    assert result["confirmed"] is True
    assert result["confirmation_group"] == "confirmed_watch"
    assert "volume_ratio_weak" in result["confirmation_fail_reasons"]
```

- [ ] **Step 2: Run the confirmation tests and verify they fail**

Run:

```bash
pytest tests/test_intraday_confirm.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.intraday_confirm'`.

- [ ] **Step 3: Implement confirmation logic**

Create `src/intraday_confirm.py`:

```python
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

    confirmed = "risk_line_broken" not in fail_reasons and len(reasons) >= 2
    result["confirmed"] = confirmed
    if confirmed and not fail_reasons:
        result["confirmation_group"] = "confirmed_core" if pending["group"] == "core" else "confirmed_watch"
    elif confirmed:
        result["confirmation_group"] = "confirmed_watch"

    result["confirmation_reasons"] = reasons
    result["confirmation_fail_reasons"] = fail_reasons
    return result
```

- [ ] **Step 4: Run the confirmation tests**

Run:

```bash
pytest tests/test_intraday_confirm.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/intraday_confirm.py tests/test_intraday_confirm.py
git commit -m "feat: add intraday snapshot confirmation"
```

---

### Task 6: Implement SQLite Storage

**Files:**
- Create: `src/storage.py`
- Test: `tests/test_storage.py`

- [ ] **Step 1: Write failing storage tests**

Create `tests/test_storage.py`:

```python
from pathlib import Path

from src.storage import (
    init_db,
    query_pending_confirmations,
    save_daily_results,
    save_intraday_results,
)


def daily_result():
    return {
        "symbol": "000001",
        "name": "Alpha",
        "mode": "A",
        "group": "core",
        "score": 88.0,
        "signal_date": "2026-06-14",
        "confirm_date": "",
        "risk_price": 10.0,
        "buy_observation_price": 10.8,
        "reasons": ["bullish_doji_signal"],
        "fail_reasons": [],
        "signal_low": 10.0,
        "signal_close": 10.8,
        "upper_trigger_price": 11.0,
    }


def test_save_daily_results_creates_pending_rows(tmp_path):
    db_path = tmp_path / "main.db"
    init_db(db_path)
    save_daily_results(db_path, "2026-06-14", [daily_result()])
    pending = query_pending_confirmations(db_path, "2026-06-14")
    assert len(pending) == 1
    assert pending[0]["symbol"] == "000001"
    assert pending[0]["mode"] == "A"


def test_save_intraday_results_persists_confirmation(tmp_path):
    db_path = tmp_path / "main.db"
    init_db(db_path)
    save_intraday_results(
        db_path,
        "2026-06-15",
        [
            {
                "screen_date": "2026-06-14",
                "symbol": "000001",
                "name": "Alpha",
                "mode": "A",
                "original_group": "core",
                "signal_date": "2026-06-14",
                "snapshot_time": "2026-06-15 14:30:00",
                "last_price": 11.0,
                "pct_chg": 2.0,
                "amount": 100000000,
                "volume_ratio": 1.1,
                "confirmed": True,
                "confirmation_group": "confirmed_core",
                "confirmation_reasons": ["mode_a_trigger_reached"],
                "confirmation_fail_reasons": [],
            }
        ],
    )
    assert Path(db_path).exists()
```

- [ ] **Step 2: Run the storage tests and verify they fail**

Run:

```bash
pytest tests/test_storage.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.storage'`.

- [ ] **Step 3: Implement SQLite storage**

Create `src/storage.py`:

```python
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


def get_conn(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | Path) -> None:
    conn = get_conn(db_path)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS daily_screen_result (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            screen_date TEXT NOT NULL,
            symbol TEXT NOT NULL,
            name TEXT,
            mode TEXT NOT NULL,
            group_name TEXT NOT NULL,
            score REAL NOT NULL,
            signal_date TEXT,
            risk_price REAL,
            buy_observation_price REAL,
            reasons_json TEXT NOT NULL,
            fail_reasons_json TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            create_time TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_daily_screen_date ON daily_screen_result(screen_date);

        CREATE TABLE IF NOT EXISTS pending_confirmation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            screen_date TEXT NOT NULL,
            symbol TEXT NOT NULL,
            name TEXT,
            mode TEXT NOT NULL,
            group_name TEXT NOT NULL,
            signal_date TEXT NOT NULL,
            signal_low REAL NOT NULL,
            signal_close REAL NOT NULL,
            risk_price REAL NOT NULL,
            upper_trigger_price REAL NOT NULL,
            payload_json TEXT NOT NULL,
            create_time TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(screen_date, symbol, mode)
        );
        CREATE INDEX IF NOT EXISTS idx_pending_screen_date ON pending_confirmation(screen_date);

        CREATE TABLE IF NOT EXISTS intraday_confirm_result (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            confirm_date TEXT NOT NULL,
            screen_date TEXT NOT NULL,
            symbol TEXT NOT NULL,
            name TEXT,
            mode TEXT NOT NULL,
            original_group TEXT,
            confirmation_group TEXT,
            confirmed INTEGER NOT NULL,
            snapshot_time TEXT,
            last_price REAL,
            pct_chg REAL,
            amount REAL,
            volume_ratio REAL,
            reasons_json TEXT NOT NULL,
            fail_reasons_json TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            create_time TEXT DEFAULT (datetime('now','localtime'))
        );
        CREATE INDEX IF NOT EXISTS idx_intraday_confirm_date ON intraday_confirm_result(confirm_date);
        """
    )
    conn.commit()
    conn.close()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def save_daily_results(db_path: str | Path, screen_date: str, results: list[dict[str, Any]]) -> None:
    conn = get_conn(db_path)
    for result in results:
        conn.execute(
            """
            INSERT INTO daily_screen_result
            (screen_date, symbol, name, mode, group_name, score, signal_date, risk_price,
             buy_observation_price, reasons_json, fail_reasons_json, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                screen_date,
                result["symbol"],
                result.get("name", ""),
                result["mode"],
                result["group"],
                result["score"],
                result.get("signal_date", ""),
                result.get("risk_price", 0.0),
                result.get("buy_observation_price", 0.0),
                _json(result.get("reasons", [])),
                _json(result.get("fail_reasons", [])),
                _json(result),
            ),
        )
        if result["group"] in {"core", "watch"}:
            conn.execute(
                """
                INSERT OR REPLACE INTO pending_confirmation
                (screen_date, symbol, name, mode, group_name, signal_date, signal_low,
                 signal_close, risk_price, upper_trigger_price, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    screen_date,
                    result["symbol"],
                    result.get("name", ""),
                    result["mode"],
                    result["group"],
                    result.get("signal_date", ""),
                    result.get("signal_low", result.get("risk_price", 0.0)),
                    result.get("signal_close", result.get("buy_observation_price", 0.0)),
                    result.get("risk_price", 0.0),
                    result.get("upper_trigger_price", result.get("buy_observation_price", 0.0)),
                    _json(result),
                ),
            )
    conn.commit()
    conn.close()


def query_pending_confirmations(db_path: str | Path, screen_date: str) -> list[dict[str, Any]]:
    conn = get_conn(db_path)
    rows = conn.execute(
        """
        SELECT screen_date, symbol, name, mode, group_name AS "group", signal_date,
               signal_low, signal_close, risk_price, upper_trigger_price, payload_json
        FROM pending_confirmation
        WHERE screen_date=?
        ORDER BY group_name, mode, symbol
        """,
        (screen_date,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def save_intraday_results(db_path: str | Path, confirm_date: str, results: list[dict[str, Any]]) -> None:
    conn = get_conn(db_path)
    for result in results:
        conn.execute(
            """
            INSERT INTO intraday_confirm_result
            (confirm_date, screen_date, symbol, name, mode, original_group,
             confirmation_group, confirmed, snapshot_time, last_price, pct_chg,
             amount, volume_ratio, reasons_json, fail_reasons_json, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                confirm_date,
                result["screen_date"],
                result["symbol"],
                result.get("name", ""),
                result["mode"],
                result.get("original_group", ""),
                result.get("confirmation_group", "not_confirmed"),
                1 if result.get("confirmed", False) else 0,
                result.get("snapshot_time", ""),
                result.get("last_price", 0.0),
                result.get("pct_chg", 0.0),
                result.get("amount", 0.0),
                result.get("volume_ratio", 0.0),
                _json(result.get("confirmation_reasons", [])),
                _json(result.get("confirmation_fail_reasons", [])),
                _json(result),
            ),
        )
    conn.commit()
    conn.close()
```

- [ ] **Step 4: Run the storage tests**

Run:

```bash
pytest tests/test_storage.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add src/storage.py tests/test_storage.py
git commit -m "feat: add sqlite persistence"
```

---

### Task 7: Implement Data Fetchers And Candidate Pool

**Files:**
- Create: `src/data_fetcher.py`
- Create: `src/candidate_pool.py`
- Create: `src/concurrency.py`
- Test: `tests/test_candidate_pool.py`

- [ ] **Step 1: Write failing candidate-pool tests**

Create `tests/test_candidate_pool.py`:

```python
import pandas as pd

from src.candidate_pool import build_mode_a_symbols, build_mode_b_candidates


def test_build_mode_a_symbols_prioritizes_limit_up_and_amount():
    limit_up = pd.DataFrame(
        [
            {"代码": "000001", "名称": "Alpha", "连板数": 2},
            {"代码": "000002", "名称": "Beta", "连板数": 1},
        ]
    )
    strong = pd.DataFrame(
        [
            {"symbol": "000002", "name": "Beta", "amount": 200000000, "rise_pct": 22.0},
            {"symbol": "000003", "name": "Gamma", "amount": 250000000, "rise_pct": 25.0},
            {"symbol": "000004", "name": "Weak", "amount": 10000000, "rise_pct": 3.0},
        ]
    )
    result = build_mode_a_symbols(limit_up, strong, min_amount=100000000, min_rise_pct=18.0)
    assert result == [
        {"symbol": "000001", "name": "Alpha", "source": "limit_up"},
        {"symbol": "000002", "name": "Beta", "source": "limit_up"},
        {"symbol": "000003", "name": "Gamma", "source": "strong_trend"},
    ]


def test_build_mode_b_candidates_maps_catalysts_to_symbols():
    rows = [{"symbol": "300000", "name": "Catalyst", "catalyst_date": "2026-06-10"}]
    result = build_mode_b_candidates(rows)
    assert result == [{"symbol": "300000", "name": "Catalyst", "source": "manual_catalyst", "catalyst": rows[0]}]
```

- [ ] **Step 2: Run the candidate-pool tests and verify they fail**

Run:

```bash
pytest tests/test_candidate_pool.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.candidate_pool'`.

- [ ] **Step 3: Implement akshare wrappers**

Create `src/data_fetcher.py`:

```python
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
        symbol = str(row.get("代码", ""))
        if symbol not in symbols:
            continue
        prev_close = float(row.get("昨收", 0) or 0)
        last_price = float(row.get("最新价", 0) or 0)
        rows[symbol] = {
            "symbol": symbol,
            "name": str(row.get("名称", "")),
            "last_price": last_price,
            "open": float(row.get("今开", 0) or 0),
            "prev_close": prev_close,
            "high": float(row.get("最高", 0) or 0),
            "low": float(row.get("最低", 0) or 0),
            "pct_chg": float(row.get("涨跌幅", 0) or 0),
            "amount": float(row.get("成交额", 0) or 0),
            "volume_ratio": float(row.get("量比", 0) or 0),
            "snapshot_time": now,
        }
    return rows
```

- [ ] **Step 4: Implement candidate pool helpers**

Create `src/candidate_pool.py`:

```python
from __future__ import annotations

import pandas as pd


def _limit_up_code(row: pd.Series) -> str:
    return str(row.get("代码", row.get("symbol", ""))).zfill(6)


def _limit_up_name(row: pd.Series) -> str:
    return str(row.get("名称", row.get("name", "")))


def build_mode_a_symbols(
    limit_up_pool: pd.DataFrame,
    strong_trend_pool: pd.DataFrame,
    min_amount: float,
    min_rise_pct: float,
) -> list[dict]:
    results: list[dict] = []
    seen: set[str] = set()

    if limit_up_pool is not None and not limit_up_pool.empty:
        for _, row in limit_up_pool.iterrows():
            symbol = _limit_up_code(row)
            if symbol in seen:
                continue
            results.append({"symbol": symbol, "name": _limit_up_name(row), "source": "limit_up"})
            seen.add(symbol)

    if strong_trend_pool is not None and not strong_trend_pool.empty:
        for _, row in strong_trend_pool.iterrows():
            symbol = str(row["symbol"]).zfill(6)
            if symbol in seen:
                continue
            if float(row.get("amount", 0)) >= min_amount and float(row.get("rise_pct", 0)) >= min_rise_pct:
                results.append({"symbol": symbol, "name": str(row.get("name", "")), "source": "strong_trend"})
                seen.add(symbol)

    return results


def build_mode_b_candidates(catalyst_rows: list[dict]) -> list[dict]:
    return [
        {
            "symbol": str(row["symbol"]).zfill(6),
            "name": str(row.get("name", "")),
            "source": "manual_catalyst",
            "catalyst": row,
        }
        for row in catalyst_rows
    ]
```

- [ ] **Step 5: Add concurrency helper**

Create `src/concurrency.py`:

```python
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from typing import Callable, Iterable, TypeVar


T = TypeVar("T")


class RateLimiter:
    def __init__(self, max_per_second: int):
        self.interval = 1.0 / max(1, max_per_second)
        self._lock = Lock()
        self._last_call = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.time()
            sleep_for = self.interval - (now - self._last_call)
            if sleep_for > 0:
                time.sleep(sleep_for)
            self._last_call = time.time()


def fetch_many(
    items: Iterable[str],
    fetcher: Callable[[str], T],
    max_workers: int,
    max_per_second: int,
) -> dict[str, T]:
    limiter = RateLimiter(max_per_second)
    results: dict[str, T] = {}

    def wrapped(item: str) -> tuple[str, T]:
        limiter.wait()
        return item, fetcher(item)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(wrapped, item) for item in items]
        for future in as_completed(futures):
            key, value = future.result()
            results[key] = value
    return results
```

- [ ] **Step 6: Run the candidate-pool tests**

Run:

```bash
pytest tests/test_candidate_pool.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add src/data_fetcher.py src/candidate_pool.py src/concurrency.py tests/test_candidate_pool.py
git commit -m "feat: add data fetcher and candidate pool"
```

---

### Task 8: Implement Reporting

**Files:**
- Create: `src/reporter.py`
- Create: `src/html_reporter.py`
- Test: `tests/test_reporter.py`

- [ ] **Step 1: Write failing reporter tests**

Create `tests/test_reporter.py`:

```python
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
    assert "Wstatus daily report 2026-06-14" in text
    assert "bullish_doji_signal" in text
```

- [ ] **Step 2: Run the reporter tests and verify they fail**

Run:

```bash
pytest tests/test_reporter.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.html_reporter'`.

- [ ] **Step 3: Implement CSV and console reporting**

Create `src/reporter.py`:

```python
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


def export_csv_report(results: list[dict[str, Any]], report_type: str, report_date: str, export_dir: str | Path) -> str:
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
```

- [ ] **Step 4: Implement HTML reporting**

Create `src/html_reporter.py`:

```python
from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any


def _format_list(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(escape(str(item)) for item in value)
    return escape(str(value))


def export_html_report(results: list[dict[str, Any]], report_type: str, report_date: str, export_dir: str | Path) -> str:
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
            f"<td>{escape(str(result.get('group', result.get('confirmation_group', ''))))}</td>"
            f"<td>{escape(str(result.get('score', '')))}</td>"
            f"<td>{escape(str(result.get('signal_date', '')))}</td>"
            f"<td>{escape(str(result.get('risk_price', '')))}</td>"
            f"<td>{_format_list(result.get('reasons', result.get('confirmation_reasons', [])))}</td>"
            f"<td>{_format_list(result.get('fail_reasons', result.get('confirmation_fail_reasons', [])))}</td>"
            "</tr>"
        )
    body = "\n".join(rows) if rows else "<tr><td colspan=\"9\">No matching candidates.</td></tr>"
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Wstatus {escape(report_type)} report {escape(report_date)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; color: #222; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background: #f5f5f5; }}
  </style>
</head>
<body>
  <h1>Wstatus {escape(report_type)} report {escape(report_date)}</h1>
  <table>
    <thead>
      <tr><th>Symbol</th><th>Name</th><th>Mode</th><th>Group</th><th>Score</th><th>Signal Date</th><th>Risk</th><th>Reasons</th><th>Fail Reasons</th></tr>
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
```

- [ ] **Step 5: Run the reporter tests**

Run:

```bash
pytest tests/test_reporter.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```bash
git add src/reporter.py src/html_reporter.py tests/test_reporter.py
git commit -m "feat: add local reports"
```

---

### Task 9: Implement Pipeline And CLI

**Files:**
- Create: `src/pipeline.py`
- Create: `main.py`
- Create: `run_daily.py`
- Create: `run_intraday.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write failing pipeline tests**

Create `tests/test_pipeline.py`:

```python
import pandas as pd

from src.pipeline import run_daily_screen_with_inputs, run_intraday_confirm_with_inputs


def mode_a_frame():
    rows = []
    close = 10.0
    for i in range(20):
        rows.append({"trade_date": f"2026-05-{i+1:02d}", "open": close, "high": close + 0.4, "low": close - 0.2, "close": close + 0.2, "volume": 800, "amount": 90000000})
        close += 0.2
    rows.append({"trade_date": "2026-05-21", "open": 14.0, "high": 18.8, "low": 13.8, "close": 18.0, "volume": 3000, "amount": 250000000})
    for day, price, volume in [
        ("2026-05-22", 17.6, 1800),
        ("2026-05-25", 17.8, 1500),
        ("2026-05-26", 17.7, 1300),
        ("2026-05-27", 17.9, 1200),
    ]:
        rows.append({"trade_date": day, "open": price - 0.1, "high": price + 0.35, "low": price - 0.35, "close": price, "volume": volume, "amount": 160000000})
    rows.append({"trade_date": "2026-05-28", "open": 18.0, "high": 18.6, "low": 17.7, "close": 18.2, "volume": 1250, "amount": 180000000})
    return pd.DataFrame(rows)


def settings():
    return {
        "paths": {"db": "", "export_dir": "", "catalyst_pool": ""},
        "params": {
            "mode_a": {
                "prior_high_window": 60,
                "min_prior_rise_pct": 18.0,
                "min_amount": 100000000,
                "consolidation_min_days": 3,
                "consolidation_max_days": 15,
                "max_pullback_pct": 18.0,
                "max_signal_body_ratio": 0.35,
                "max_signal_amplitude_pct": 9.0,
                "volume_shrink_threshold": 1.10,
                "upper_trigger_buffer_pct": 1.0,
            },
            "mode_b": {
                "crash_window_days": 5,
                "min_crash_pct": 14.0,
                "max_signal_body_ratio": 0.30,
                "max_signal_amplitude_pct": 10.0,
                "shrink_volume_ratio": 0.75,
                "signal_after_crash_days": 2,
            },
            "intraday": {
                "repair_buffer_pct": -1.0,
                "amount_min_ratio": 0.80,
                "volume_ratio_min": 0.80,
            },
        },
    }


def test_run_daily_screen_with_inputs_returns_core_candidate():
    results = run_daily_screen_with_inputs(
        screen_date="2026-05-28",
        mode_a_candidates=[{"symbol": "000001", "name": "Alpha", "source": "limit_up"}],
        mode_b_candidates=[],
        daily_frames={"000001": mode_a_frame()},
        settings=settings(),
    )
    assert results[0]["symbol"] == "000001"
    assert results[0]["group"] == "core"


def test_run_intraday_confirm_with_inputs_returns_confirmation():
    pending = [
        {
            "screen_date": "2026-05-28",
            "symbol": "000001",
            "name": "Alpha",
            "mode": "A",
            "group": "core",
            "signal_date": "2026-05-28",
            "signal_low": 17.7,
            "signal_close": 18.2,
            "risk_price": 17.55,
            "upper_trigger_price": 18.5,
            "payload_json": "{}",
        }
    ]
    snapshots = {
        "000001": {
            "symbol": "000001",
            "name": "Alpha",
            "last_price": 18.6,
            "open": 18.0,
            "prev_close": 18.2,
            "high": 18.7,
            "low": 18.0,
            "pct_chg": 2.2,
            "amount": 180000000,
            "volume_ratio": 1.1,
            "snapshot_time": "2026-05-29 14:30:00",
        }
    }
    results = run_intraday_confirm_with_inputs(pending, snapshots, settings())
    assert results[0]["confirmation_group"] == "confirmed_core"
```

- [ ] **Step 2: Run the pipeline tests and verify they fail**

Run:

```bash
pytest tests/test_pipeline.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'src.pipeline'`.

- [ ] **Step 3: Implement pure-input pipeline functions and real runners**

Create `src/pipeline.py`:

```python
from __future__ import annotations

from datetime import date
from typing import Any

from src.candidate_pool import build_mode_a_symbols, build_mode_b_candidates
from src.config import load_settings
from src.data_fetcher import fetch_daily_kline, fetch_limit_up_pool, fetch_realtime_snapshots, fetch_trading_calendar, resolve_trading_day
from src.html_reporter import export_html_report
from src.intraday_confirm import confirm_pending
from src.reporter import export_csv_report, print_report
from src.storage import init_db, query_pending_confirmations, save_daily_results, save_intraday_results
from src.strategy_a import analyze_mode_a
from src.strategy_b import load_catalyst_pool, analyze_mode_b


def run_daily_screen_with_inputs(
    screen_date: str,
    mode_a_candidates: list[dict[str, Any]],
    mode_b_candidates: list[dict[str, Any]],
    daily_frames: dict[str, Any],
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for candidate in mode_a_candidates:
        frame = daily_frames.get(candidate["symbol"])
        if frame is None:
            continue
        results.append(analyze_mode_a(candidate["symbol"], candidate.get("name", ""), frame, settings["params"]["mode_a"]))
    for candidate in mode_b_candidates:
        frame = daily_frames.get(candidate["symbol"])
        if frame is None:
            continue
        results.append(analyze_mode_b(candidate["catalyst"], frame, settings["params"]["mode_b"]))
    return sorted(results, key=lambda row: (row["group"] != "core", row["group"] != "watch", -row["score"], row["symbol"]))


def run_intraday_confirm_with_inputs(
    pending_rows: list[dict[str, Any]],
    snapshots: dict[str, dict[str, Any]],
    settings: dict[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for pending in pending_rows:
        snapshot = snapshots.get(pending["symbol"])
        if snapshot is None:
            missing = {
                "screen_date": pending["screen_date"],
                "symbol": pending["symbol"],
                "name": pending["name"],
                "mode": pending["mode"],
                "original_group": pending["group"],
                "signal_date": pending["signal_date"],
                "snapshot_time": "",
                "last_price": 0.0,
                "pct_chg": 0.0,
                "amount": 0.0,
                "volume_ratio": 0.0,
                "confirmed": False,
                "confirmation_group": "not_confirmed",
                "confirmation_reasons": [],
                "confirmation_fail_reasons": ["snapshot_missing"],
            }
            results.append(missing)
            continue
        results.append(confirm_pending(pending, snapshot, settings["params"]["intraday"]))
    return results


def run_daily_screen(screen_date: str | None = None, settings_path: str | None = None) -> list[dict[str, Any]]:
    settings = load_settings(settings_path)
    today = screen_date or date.today().isoformat()
    trade_dates = fetch_trading_calendar()
    actual_date = resolve_trading_day(trade_dates, today)
    db_path = settings["paths"]["db"]
    export_dir = settings["paths"]["export_dir"]
    init_db(db_path)

    limit_pool = fetch_limit_up_pool(actual_date)
    strong_pool = limit_pool.rename(columns={"代码": "symbol", "名称": "name"}) if limit_pool is not None else None
    mode_a_candidates = build_mode_a_symbols(
        limit_pool,
        strong_pool,
        min_amount=settings["params"]["mode_a"]["min_amount"],
        min_rise_pct=settings["params"]["mode_a"]["min_prior_rise_pct"],
    )
    catalyst_rows, catalyst_issues = load_catalyst_pool(settings["paths"]["catalyst_pool"], actual_date)
    mode_b_candidates = build_mode_b_candidates(catalyst_rows)
    all_symbols = sorted({candidate["symbol"] for candidate in mode_a_candidates + mode_b_candidates})
    frames = {
        symbol: fetch_daily_kline(symbol, calendar_days=settings["runtime"]["calendar_days"])
        for symbol in all_symbols
    }
    results = run_daily_screen_with_inputs(actual_date, mode_a_candidates, mode_b_candidates, frames, settings)
    save_daily_results(db_path, actual_date, results)
    print_report(results, f"Wstatus daily screening {actual_date}")
    export_csv_report(results, "daily", actual_date, export_dir)
    export_html_report(results, "daily", actual_date, export_dir)
    if catalyst_issues:
        print(f"Catalyst import issues: {len(catalyst_issues)}")
    return results


def run_intraday_confirm(confirm_date: str | None = None, settings_path: str | None = None, screen_date: str | None = None) -> list[dict[str, Any]]:
    settings = load_settings(settings_path)
    today = confirm_date or date.today().isoformat()
    db_path = settings["paths"]["db"]
    export_dir = settings["paths"]["export_dir"]
    init_db(db_path)
    pending_date = screen_date or today
    pending = query_pending_confirmations(db_path, pending_date)
    snapshots = fetch_realtime_snapshots([row["symbol"] for row in pending])
    results = run_intraday_confirm_with_inputs(pending, snapshots, settings)
    save_intraday_results(db_path, today, results)
    print_report(results, f"Wstatus intraday confirmation {today}")
    export_csv_report(results, "intraday", today, export_dir)
    export_html_report(results, "intraday", today, export_dir)
    return results
```

- [ ] **Step 4: Implement CLI wrappers**

Create `main.py`:

```python
from __future__ import annotations

import argparse
import sys

from src.pipeline import run_daily_screen, run_intraday_confirm


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Wstatus dual-mode right-side stock screener")
    parser.add_argument("--mode", choices=["daily", "intraday"], default="daily")
    parser.add_argument("--date", default=None, help="Run date in YYYY-MM-DD format")
    parser.add_argument("--screen-date", default=None, help="Daily screen date to confirm during intraday mode")
    parser.add_argument("--settings", default=None, help="Path to settings YAML")
    args = parser.parse_args()

    if args.mode == "daily":
        run_daily_screen(screen_date=args.date, settings_path=args.settings)
    else:
        run_intraday_confirm(confirm_date=args.date, settings_path=args.settings, screen_date=args.screen_date)


if __name__ == "__main__":
    main()
```

Create `run_daily.py`:

```python
from src.pipeline import run_daily_screen


if __name__ == "__main__":
    run_daily_screen()
```

Create `run_intraday.py`:

```python
from src.pipeline import run_intraday_confirm


if __name__ == "__main__":
    run_intraday_confirm()
```

- [ ] **Step 5: Run pipeline tests**

Run:

```bash
pytest tests/test_pipeline.py -v
```

Expected: PASS.

- [ ] **Step 6: Run the full test suite**

Run:

```bash
pytest -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

Run:

```bash
git add src/pipeline.py main.py run_daily.py run_intraday.py tests/test_pipeline.py
git commit -m "feat: add screening pipelines and cli"
```

---

### Task 10: Final Verification And Documentation Pass

**Files:**
- Modify: `docs/superpowers/specs/2026-06-14-wstatus-dual-mode-right-side-design.md` if implementation discoveries require clarifying a non-behavioral detail.
- Modify: `docs/superpowers/plans/2026-06-14-wstatus-dual-mode-right-side-implementation.md` only to check off completed steps during execution.

- [ ] **Step 1: Run all tests**

Run:

```bash
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run daily CLI smoke test**

Run:

```bash
python main.py --mode daily --date 2026-06-14
```

Expected: command exits without Python tracebacks. If akshare has no data for the date or network is unavailable, the command prints a fetch/data message and still writes an empty local report.

- [ ] **Step 3: Run intraday CLI smoke test**

Run:

```bash
python main.py --mode intraday --date 2026-06-14 --screen-date 2026-06-14
```

Expected: command exits without Python tracebacks. If no pending confirmations exist, the command prints "No matching candidates." and writes an empty local report.

- [ ] **Step 4: Check Linux-compatible scheduler commands**

From a Linux checkout, these cron entries should be valid after dependencies are installed:

```cron
0 20 * * 1-5 cd /path/to/wstatus && /usr/bin/python3 main.py --mode daily >> logs/daily.log 2>&1
30 14 * * 1-5 cd /path/to/wstatus && /usr/bin/python3 main.py --mode intraday >> logs/intraday.log 2>&1
```

Expected: commands use project-relative execution and do not rely on Windows paths.

- [ ] **Step 5: Inspect generated outputs**

Run:

```bash
Get-ChildItem -Path data/export -Force
```

Expected: output includes one or more `daily_*.csv`, `daily_*.html`, `intraday_*.csv`, or `intraday_*.html` files after smoke runs.

- [ ] **Step 6: Check git status**

Run:

```bash
git status --short
```

Expected: only intentional generated files are untracked. `data/export/` and `db/*.db` should be ignored by `.gitignore`.

- [ ] **Step 7: Commit final verification notes if any tracked docs changed**

Run only if tracked docs changed:

```bash
git add docs/superpowers/specs/2026-06-14-wstatus-dual-mode-right-side-design.md docs/superpowers/plans/2026-06-14-wstatus-dual-mode-right-side-implementation.md
git commit -m "docs: update wstatus implementation notes"
```

Expected: commit succeeds if there are tracked documentation changes. If there are no tracked changes, skip this command.

---

## Verification

After all tasks are complete, run:

```bash
pytest -v
python main.py --mode daily --date 2026-06-14
python main.py --mode intraday --date 2026-06-14 --screen-date 2026-06-14
git status --short
```

Success means:

- All tests pass.
- The daily CLI exits cleanly and writes local reports.
- The intraday CLI exits cleanly and writes local reports.
- Generated reports and SQLite files are ignored.
- The final git status contains no unexpected tracked changes.

## Implementation Order

Implement tasks in order. Each task leaves the repository in a working state and has its own commit. Do not begin the next task while the current task has failing tests.

## Next Skill

Use `$superpower-subagents` for subagent-driven implementation or `$superpower-executing-plans` for inline execution.

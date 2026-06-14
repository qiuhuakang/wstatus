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

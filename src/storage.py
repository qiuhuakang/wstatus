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

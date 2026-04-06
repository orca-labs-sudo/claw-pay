'use strict' if False else None  # Python, not JS

"""
Einfaches SQLite Transaction Log.
Speichert jeden /settle Aufruf (Erfolg + Fehler) persistent.
"""

import sqlite3
import os
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = os.getenv("TX_LOG_PATH", "/data/transactions.db")


def _conn():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ts          TEXT    NOT NULL,
                success     INTEGER NOT NULL,
                payer       TEXT,
                seller      TEXT,
                gross       TEXT,
                seller_amt  TEXT,
                fee         TEXT,
                network     TEXT,
                intake_tx   TEXT,
                transfer_tx TEXT,
                error       TEXT
            )
        """)
        conn.commit()


def log_settlement(
    success: bool,
    payer: str = None,
    seller: str = None,
    gross: str = None,
    seller_amt: str = None,
    fee: str = None,
    network: str = None,
    intake_tx: str = None,
    transfer_tx: str = None,
    error: str = None,
):
    with _conn() as conn:
        conn.execute("""
            INSERT INTO transactions
              (ts, success, payer, seller, gross, seller_amt, fee, network, intake_tx, transfer_tx, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now(timezone.utc).isoformat(),
            1 if success else 0,
            payer, seller, gross, seller_amt, fee, network,
            intake_tx, transfer_tx, error,
        ))
        conn.commit()


def get_stats():
    with _conn() as conn:
        total     = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
        success   = conn.execute("SELECT COUNT(*) FROM transactions WHERE success=1").fetchone()[0]
        errors    = conn.execute("SELECT COUNT(*) FROM transactions WHERE success=0").fetchone()[0]
        volume    = conn.execute("SELECT SUM(CAST(gross AS REAL)) FROM transactions WHERE success=1").fetchone()[0] or 0
        fees      = conn.execute("SELECT SUM(CAST(fee  AS REAL)) FROM transactions WHERE success=1").fetchone()[0] or 0
        return {
            "total": total,
            "success": success,
            "errors": errors,
            "volume_usd": round(volume, 6),
            "fees_usd": round(fees, 6),
        }


def get_recent(limit=50):
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM transactions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

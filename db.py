"""
db.py — SQLite storage with a single transactions table.

All paths are resolved relative to this file so it works from any CWD.
"""

import os
import sqlite3
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'expenses.db')


def _connect():
    """Return a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the transactions table if it does not exist."""
    conn = _connect()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS txns (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT    NOT NULL,
            category    TEXT    NOT NULL,
            amount      REAL    NOT NULL,
            note        TEXT,
            type        TEXT    NOT NULL DEFAULT 'expense',
            chat_id     INTEGER,
            created_at  TEXT    NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def add(date_str: str, category: str, amount: float,
        note: str, txn_type: str, chat_id: int) -> int:
    """
    Insert a new transaction and return the new row id.

    Parameters
    ----------
    date_str : str   — ISO date string, e.g. '2026-06-28'
    category : str   — expense category
    amount   : float — transaction amount
    note     : str   — human-readable note
    txn_type : str   — 'expense' or 'income'
    chat_id  : int   — Telegram chat id (for undo scoping)
    """
    conn = _connect()
    cur = conn.execute(
        '''INSERT INTO txns (date, category, amount, note, type, chat_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (date_str, category, amount, note, txn_type, chat_id,
         datetime.now().isoformat()),
    )
    row_id = cur.lastrowid
    conn.commit()
    conn.close()
    return row_id


def undo_last(chat_id: int) -> dict | None:
    """
    Delete the most recently added transaction for *chat_id*.

    Returns the deleted row as a dict, or None if nothing to undo.
    """
    conn = _connect()
    row = conn.execute(
        '''SELECT * FROM txns WHERE chat_id = ? ORDER BY id DESC LIMIT 1''',
        (chat_id,),
    ).fetchone()

    if row is None:
        conn.close()
        return None

    deleted = dict(row)
    conn.execute('DELETE FROM txns WHERE id = ?', (row['id'],))
    conn.commit()
    conn.close()
    return deleted


def all_rows() -> list[dict]:
    """Return every transaction as a list of dicts, newest first."""
    conn = _connect()
    rows = conn.execute(
        'SELECT * FROM txns ORDER BY date DESC, id DESC',
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def month_rows(month_str: str) -> list[dict]:
    """
    Return transactions for a given month.

    Parameters
    ----------
    month_str : str — e.g. '2026-06'
    """
    conn = _connect()
    rows = conn.execute(
        '''SELECT * FROM txns
           WHERE strftime('%Y-%m', date) = ?
           ORDER BY date DESC, id DESC''',
        (month_str,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def month_total(month_str: str) -> float:
    """
    Return the sum of expense amounts for a given month.

    Only rows with type='expense' are counted.
    """
    conn = _connect()
    result = conn.execute(
        '''SELECT COALESCE(SUM(amount), 0) AS total
           FROM txns
           WHERE strftime('%Y-%m', date) = ?
             AND type = 'expense' ''',
        (month_str,),
    ).fetchone()
    conn.close()
    return float(result['total'])

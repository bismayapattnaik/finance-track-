"""
test_db.py — Tests for db.py using a temporary SQLite database.

Run with: pytest test_db.py -v
"""

import os
import tempfile
import pytest
import db as db_module


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    """
    Redirect the database to a temporary file for each test.
    This ensures tests are isolated and don't touch the real database.
    """
    temp_db = str(tmp_path / 'test_expenses.db')
    monkeypatch.setattr(db_module, 'DB_PATH', temp_db)
    db_module.init_db()
    yield


# ═══════════════════════════════════════════════════════════════════════════
# init_db
# ═══════════════════════════════════════════════════════════════════════════

class TestInitDB:
    """Test database initialisation."""

    def test_creates_table(self):
        """init_db should create the txns table."""
        import sqlite3
        conn = sqlite3.connect(db_module.DB_PATH)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='txns'"
        )
        assert cur.fetchone() is not None
        conn.close()

    def test_idempotent(self):
        """Calling init_db twice should not raise."""
        db_module.init_db()  # Already called in fixture
        db_module.init_db()  # Should be safe


# ═══════════════════════════════════════════════════════════════════════════
# add
# ═══════════════════════════════════════════════════════════════════════════

class TestAdd:
    """Test inserting transactions."""

    def test_returns_id(self):
        row_id = db_module.add('2026-06-28', 'food', 450, 'swiggy', 'expense', 12345)
        assert row_id is not None
        assert isinstance(row_id, int)
        assert row_id >= 1

    def test_sequential_ids(self):
        id1 = db_module.add('2026-06-28', 'food', 450, 'swiggy', 'expense', 12345)
        id2 = db_module.add('2026-06-28', 'travel', 300, 'ola', 'expense', 12345)
        assert id2 > id1

    def test_stores_all_fields(self):
        db_module.add('2026-06-28', 'food', 450, 'swiggy biryani', 'expense', 99)
        rows = db_module.all_rows()
        assert len(rows) == 1
        row = rows[0]
        assert row['date'] == '2026-06-28'
        assert row['category'] == 'food'
        assert row['amount'] == 450
        assert row['note'] == 'swiggy biryani'
        assert row['type'] == 'expense'
        assert row['chat_id'] == 99


# ═══════════════════════════════════════════════════════════════════════════
# undo_last
# ═══════════════════════════════════════════════════════════════════════════

class TestUndoLast:
    """Test undo (delete most recent for a chat_id)."""

    def test_deletes_most_recent(self):
        db_module.add('2026-06-28', 'food', 100, 'a', 'expense', 1)
        db_module.add('2026-06-28', 'travel', 200, 'b', 'expense', 1)
        deleted = db_module.undo_last(1)
        assert deleted is not None
        assert deleted['amount'] == 200
        assert deleted['note'] == 'b'
        # Only one row should remain
        rows = db_module.all_rows()
        assert len(rows) == 1
        assert rows[0]['amount'] == 100

    def test_returns_none_when_empty(self):
        deleted = db_module.undo_last(999)
        assert deleted is None

    def test_scoped_to_chat_id(self):
        db_module.add('2026-06-28', 'food', 100, 'a', 'expense', 1)
        db_module.add('2026-06-28', 'food', 200, 'b', 'expense', 2)
        # Undo for chat_id=1 should only affect chat_id=1's entry
        deleted = db_module.undo_last(1)
        assert deleted is not None
        assert deleted['amount'] == 100
        # chat_id=2's entry should remain
        rows = db_module.all_rows()
        assert len(rows) == 1
        assert rows[0]['chat_id'] == 2


# ═══════════════════════════════════════════════════════════════════════════
# all_rows
# ═══════════════════════════════════════════════════════════════════════════

class TestAllRows:
    """Test retrieving all rows."""

    def test_returns_all(self):
        db_module.add('2026-06-01', 'food', 100, 'a', 'expense', 1)
        db_module.add('2026-06-15', 'travel', 200, 'b', 'expense', 1)
        db_module.add('2026-06-28', 'bills', 300, 'c', 'expense', 1)
        rows = db_module.all_rows()
        assert len(rows) == 3

    def test_ordered_by_date_desc(self):
        db_module.add('2026-06-01', 'food', 100, 'first', 'expense', 1)
        db_module.add('2026-06-28', 'food', 200, 'last', 'expense', 1)
        rows = db_module.all_rows()
        assert rows[0]['date'] == '2026-06-28'
        assert rows[1]['date'] == '2026-06-01'

    def test_empty_db(self):
        rows = db_module.all_rows()
        assert rows == []

    def test_returns_dicts(self):
        db_module.add('2026-06-28', 'food', 100, 'a', 'expense', 1)
        rows = db_module.all_rows()
        assert isinstance(rows[0], dict)
        assert 'id' in rows[0]
        assert 'date' in rows[0]


# ═══════════════════════════════════════════════════════════════════════════
# month_rows
# ═══════════════════════════════════════════════════════════════════════════

class TestMonthRows:
    """Test filtering by month."""

    def test_filters_correctly(self):
        db_module.add('2026-06-01', 'food', 100, 'june', 'expense', 1)
        db_module.add('2026-06-28', 'food', 200, 'june', 'expense', 1)
        db_module.add('2026-07-01', 'food', 300, 'july', 'expense', 1)
        rows = db_module.month_rows('2026-06')
        assert len(rows) == 2
        for r in rows:
            assert r['date'].startswith('2026-06')

    def test_empty_month(self):
        db_module.add('2026-06-28', 'food', 100, 'a', 'expense', 1)
        rows = db_module.month_rows('2025-01')
        assert rows == []

    def test_includes_income(self):
        db_module.add('2026-06-01', 'other', 75000, 'salary', 'income', 1)
        db_module.add('2026-06-15', 'food', 500, 'dinner', 'expense', 1)
        rows = db_module.month_rows('2026-06')
        assert len(rows) == 2


# ═══════════════════════════════════════════════════════════════════════════
# month_total
# ═══════════════════════════════════════════════════════════════════════════

class TestMonthTotal:
    """Test monthly expense total calculation."""

    def test_sums_expenses(self):
        db_module.add('2026-06-01', 'food', 100, 'a', 'expense', 1)
        db_module.add('2026-06-15', 'travel', 200, 'b', 'expense', 1)
        db_module.add('2026-06-28', 'bills', 300, 'c', 'expense', 1)
        total = db_module.month_total('2026-06')
        assert total == 600

    def test_excludes_income(self):
        db_module.add('2026-06-01', 'food', 500, 'dinner', 'expense', 1)
        db_module.add('2026-06-01', 'other', 75000, 'salary', 'income', 1)
        total = db_module.month_total('2026-06')
        assert total == 500  # Only expense, not income

    def test_excludes_other_months(self):
        db_module.add('2026-06-01', 'food', 100, 'june', 'expense', 1)
        db_module.add('2026-07-01', 'food', 999, 'july', 'expense', 1)
        total = db_module.month_total('2026-06')
        assert total == 100

    def test_zero_for_empty_month(self):
        total = db_module.month_total('2025-01')
        assert total == 0

    def test_returns_float(self):
        db_module.add('2026-06-28', 'food', 99.50, 'a', 'expense', 1)
        total = db_module.month_total('2026-06')
        assert isinstance(total, float)
        assert total == pytest.approx(99.50)

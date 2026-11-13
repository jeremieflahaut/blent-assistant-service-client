import sqlite3

import pytest

import db

REAL_DB_URI = db.DB_URI


def test_connection_is_read_only(monkeypatch):
    monkeypatch.setattr(db, "DB_URI", REAL_DB_URI)
    conn = db.get_connection()
    try:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("DELETE FROM orders")
    finally:
        conn.rollback()
        conn.close()

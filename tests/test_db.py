import sqlite3

import pytest

import db

# Capturé à l'import, avant que la fixture ne remplace DB_URI par la base de test
REAL_DB_URI = db.DB_URI


def test_connection_is_read_only(monkeypatch):
    monkeypatch.setattr(db, "DB_URI", REAL_DB_URI)
    conn = db.get_connection()
    try:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("DELETE FROM orders")
    finally:
        # Filet de sécurité : si la lecture seule était cassée, rien n'est écrit
        conn.rollback()
        conn.close()

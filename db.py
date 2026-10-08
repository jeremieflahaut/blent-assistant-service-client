import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "orders.db"
DB_URI = f"{DB_PATH.as_uri()}?mode=ro"


def get_connection() -> sqlite3.Connection:
    """Ouvre une connexion en lecture seule à la base des commandes."""
    return sqlite3.connect(DB_URI, uri=True)

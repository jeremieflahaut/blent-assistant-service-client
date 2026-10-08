import sqlite3

import pytest

import db

# Même schéma que data/orders.db (généré par pandas.to_sql : colonne "index",
# aucune clé déclarée, zip_code en INTEGER)
SCHEMA = """
CREATE TABLE "users" (
    "index" INTEGER,
    "user_id" INTEGER,
    "first_name" TEXT,
    "last_name" TEXT,
    "joining_date" TIMESTAMP,
    "phone" INTEGER,
    "email" TEXT,
    "address" TEXT,
    "city" TEXT,
    "zip_code" INTEGER
);
CREATE TABLE "orders" (
    "index" INTEGER,
    "order_id" INTEGER,
    "user_id" INTEGER,
    "status" TEXT,
    "date_purchase" TIMESTAMP,
    "date_shipped" TIMESTAMP,
    "date_delivered" TIMESTAMP
);
"""

USERS = [
    (
        0,
        1,
        "Ramona",
        "Howell",
        "2024-05-27 14:15:52",
        686855635,
        "ramona@example.net",
        "6096 Inceptos Ave",
        "Le Puy-en-Velay",
        78971,
    ),
    (
        1,
        2,
        "Ella",
        "Hampton",
        "2023-09-29 19:17:17",
        613555748,
        "ella@example.net",
        "157 Semper Rd.",
        "Alençon",
        6843,
    ),
    (
        2,
        3,
        "Xander",
        "Bradshaw",
        "2024-02-04 07:54:50",
        607687245,
        "xander@example.net",
        "4586 Nunc St.",
        "Épinal",
        88077,
    ),
]

# Commandes du client 1 insérées dans le désordre ; le client 2 a une commande ;
# le client 3 n'en a aucune
ORDERS = [
    (
        0,
        10,
        1,
        "delivered",
        "2024-05-06 16:35:08",
        "2024-05-08 16:35:08",
        "2024-05-22 16:35:08",
    ),
    (
        1,
        11,
        2,
        "delivered",
        "2024-05-10 09:00:00",
        "2024-05-11 09:00:00",
        "2024-05-20 09:00:00",
    ),
    (2, 12, 1, "invoiced", "2024-05-30 10:53:38", None, None),
    (3, 13, 1, "shipped", "2024-05-20 12:41:11", "2024-05-23 12:41:11", None),
]


# Base en mémoire partagée entre connexions : la fonction testée ouvre la sienne
TEST_DB_URI = "file:test_orders?mode=memory&cache=shared"


@pytest.fixture(autouse=True)
def test_db(monkeypatch):
    # Cette connexion garde la base en vie pendant le test
    conn = sqlite3.connect(TEST_DB_URI, uri=True)
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", USERS)
    conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?)", ORDERS)
    conn.commit()

    monkeypatch.setattr(db, "DB_URI", TEST_DB_URI)
    yield conn
    conn.close()

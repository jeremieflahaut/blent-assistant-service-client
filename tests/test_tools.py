import sqlite3

import pytest

import tools
from tools import french_date, get_customer_orders

CUSTOMER_WITH_ORDERS = 1
OTHER_CUSTOMER = 2
CUSTOMER_WITHOUT_ORDER = 3


def test_returns_orders(monkeypatch):
    monkeypatch.setenv("SIMULATED_TODAY", "2024-06-01")
    orders = get_customer_orders(CUSTOMER_WITH_ORDERS)

    assert orders[0] == {
        "order_id": 12,
        "status": "invoiced",
        "date_purchase": "30 mai 2024",
        "date_shipped": None,
        "date_delivered": None,
        "days_since_purchase": 2,
        "days_since_shipped": None,
        "days_since_delivered": None,
    }


def test_orders_sorted_from_most_recent():
    orders = get_customer_orders(CUSTOMER_WITH_ORDERS)

    assert [order["order_id"] for order in orders] == [12, 13, 10]


def test_only_returns_customer_orders():
    orders = get_customer_orders(OTHER_CUSTOMER)

    assert [order["order_id"] for order in orders] == [11]


def test_customer_without_order():
    assert get_customer_orders(CUSTOMER_WITHOUT_ORDER) == []


def test_no_internal_identifier_returned():
    for order in get_customer_orders(CUSTOMER_WITH_ORDERS):
        assert "user_id" not in order
        assert "index" not in order


def test_days_since_each_date(monkeypatch):
    monkeypatch.setenv("SIMULATED_TODAY", "2024-06-01")
    orders = get_customer_orders(CUSTOMER_WITH_ORDERS)

    order = next(order for order in orders if order["order_id"] == 10)
    assert order["days_since_purchase"] == 26
    assert order["days_since_shipped"] == 24
    assert order["days_since_delivered"] == 10


def test_french_date():
    assert french_date("2024-05-18 20:47:48") == "18 mai 2024"
    assert french_date("2024-06-01 08:00:00") == "1er juin 2024"
    assert french_date(None) is None


class FailingConnection:
    """Connexion dont toute requête échoue, et qui note si elle a été fermée."""

    closed = False

    def cursor(self):
        return self

    def execute(self, *args):
        raise sqlite3.OperationalError("database is locked")

    def close(self):
        self.closed = True


def test_connection_closed_when_query_fails(monkeypatch):
    conn = FailingConnection()
    monkeypatch.setattr(tools, "get_connection", lambda: conn)

    with pytest.raises(sqlite3.OperationalError):
        get_customer_orders(CUSTOMER_WITH_ORDERS)

    assert conn.closed

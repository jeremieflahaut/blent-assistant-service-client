from tools import get_customer_orders_and_address

# Clients de la base de test (tests/conftest.py)
CUSTOMER_WITH_ORDERS = 1
CUSTOMER_WITH_SHORT_ZIP_CODE = 2
CUSTOMER_WITHOUT_ORDER = 3


def test_returns_address_and_orders():
    result = get_customer_orders_and_address(CUSTOMER_WITH_ORDERS)

    assert result["address"] == {
        "address": "6096 Inceptos Ave",
        "city": "Le Puy-en-Velay",
        "zip_code": "78971",
    }
    assert result["orders"][0] == {
        "order_id": 12,
        "status": "invoiced",
        "date_purchase": "2024-05-30 10:53:38",
        "date_shipped": None,
        "date_delivered": None,
    }


def test_orders_sorted_from_most_recent():
    result = get_customer_orders_and_address(CUSTOMER_WITH_ORDERS)

    assert [order["order_id"] for order in result["orders"]] == [12, 13, 10]


def test_only_returns_customer_orders():
    result = get_customer_orders_and_address(CUSTOMER_WITH_SHORT_ZIP_CODE)

    assert [order["order_id"] for order in result["orders"]] == [11]


def test_customer_without_order():
    result = get_customer_orders_and_address(CUSTOMER_WITHOUT_ORDER)

    assert result["orders"] == []
    assert result["address"]["city"] == "Épinal"


def test_zip_code_keeps_leading_zero():
    result = get_customer_orders_and_address(CUSTOMER_WITH_SHORT_ZIP_CODE)

    assert result["address"]["zip_code"] == "06843"


def test_no_internal_identifier_returned():
    result = get_customer_orders_and_address(CUSTOMER_WITH_ORDERS)

    assert set(result["address"]) == {"address", "city", "zip_code"}
    for order in result["orders"]:
        assert "user_id" not in order
        assert "index" not in order

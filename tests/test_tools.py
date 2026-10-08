from tools import get_customer_orders_and_address

# Données de référence lues dans data/orders.db (base fournie, en lecture seule)
CUSTOMER_WITH_ONE_ORDER = 1
CUSTOMER_WITH_FOUR_ORDERS = 5
CUSTOMER_WITHOUT_ORDER = 19
CUSTOMER_WITH_SHORT_ZIP_CODE = 12


def test_returns_address_and_orders():
    result = get_customer_orders_and_address(CUSTOMER_WITH_ONE_ORDER)

    assert result["address"] == {
        "address": "6096 Inceptos Ave",
        "city": "Le Puy-en-Velay",
        "zip_code": "78971",
    }
    assert result["orders"] == [
        {
            "order_id": 13,
            "status": "shipped",
            "date_purchase": "2024-05-30 10:53:38",
            "date_shipped": "2024-05-31 10:53:38",
            "date_delivered": None,
        }
    ]


def test_orders_sorted_from_most_recent():
    result = get_customer_orders_and_address(CUSTOMER_WITH_FOUR_ORDERS)

    assert [order["order_id"] for order in result["orders"]] == [86, 10, 21, 81]


def test_customer_without_order():
    result = get_customer_orders_and_address(CUSTOMER_WITHOUT_ORDER)

    assert result["orders"] == []
    assert result["address"]["city"] == "Épernay"


def test_zip_code_keeps_leading_zero():
    result = get_customer_orders_and_address(CUSTOMER_WITH_SHORT_ZIP_CODE)

    assert result["address"]["zip_code"] == "06843"


def test_no_internal_identifier_returned():
    result = get_customer_orders_and_address(CUSTOMER_WITH_ONE_ORDER)

    assert set(result["address"]) == {"address", "city", "zip_code"}
    for order in result["orders"]:
        assert "user_id" not in order
        assert "index" not in order

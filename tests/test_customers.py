from customers import list_customers


def test_lists_customers_sorted_by_last_name():
    customers = list_customers()

    assert [customer["last_name"] for customer in customers] == [
        "Bradshaw",
        "Hampton",
        "Howell",
    ]
    assert customers[0] == {
        "user_id": 3,
        "first_name": "Xander",
        "last_name": "Bradshaw",
        "email": "xander@example.net",
    }

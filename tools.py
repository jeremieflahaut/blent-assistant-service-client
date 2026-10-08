import sqlite3


def get_customer_orders_and_address(user_id: int) -> dict:
    """Renvoie l'adresse actuelle du client connecté et toutes ses commandes.

    Les commandes sont triées de la plus récente à la plus ancienne. La liste
    est vide si le client n'a passé aucune commande.
    """

    conn = sqlite3.connect("file:data/orders.db?mode=ro", uri=True)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT order_id, status, date_purchase, date_shipped, date_delivered
        FROM orders
        WHERE user_id = ?
        ORDER BY date_purchase DESC
        """,
        (user_id,),
    )
    orders = cursor.fetchall()
    cursor.execute(
        "SELECT address, city, zip_code FROM users WHERE user_id = ?", (user_id,)
    )
    user = cursor.fetchone()
    conn.close()

    address = {"address": user[0], "city": user[1], "zip_code": str(user[2]).zfill(5)}

    orders_list = []

    for order in orders:
        order_dict = {
            "order_id": order[0],
            "status": order[1],
            "date_purchase": order[2],
            "date_shipped": order[3],
            "date_delivered": order[4],
        }
        orders_list.append(order_dict)

    return {"address": address, "orders": orders_list}

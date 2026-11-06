from datetime import date

from config import get_today
from db import get_connection


def get_customer_orders_and_address(user_id: int) -> dict:
    """Renvoie l'adresse actuelle du client connecté et toutes ses commandes.

    Les commandes sont triées de la plus récente à la plus ancienne. La liste
    est vide si le client n'a passé aucune commande. Les durées (days_since_*) sont
    calculées ici, à partir de la date du jour, pour que le LLM n'ait rien à calculer.
    """

    conn = get_connection()
    try:
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
    finally:
        conn.close()

    address = {"address": user[0], "city": user[1], "zip_code": str(user[2]).zfill(5)}

    today = get_today()
    orders_list = []

    for order in orders:
        order_dict = {
            "order_id": order[0],
            "status": order[1],
            "date_purchase": order[2],
            "date_shipped": order[3],
            "date_delivered": order[4],
            "days_since_purchase": days_since(order[2], today),
            "days_since_shipped": days_since(order[3], today),
            "days_since_delivered": days_since(order[4], today),
        }
        orders_list.append(order_dict)

    return {"address": address, "orders": orders_list}


def days_since(timestamp: str | None, today: date) -> int | None:
    """Nombre de jours entre une date de la base (« 2024-05-18 20:47:48 ») et today."""
    if timestamp is None:
        return None
    return (today - date.fromisoformat(timestamp[:10])).days

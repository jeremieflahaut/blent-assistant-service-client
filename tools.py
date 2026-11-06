from datetime import date

from config import get_today
from db import get_connection

MONTHS = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]


def get_customer_orders_and_address(user_id: int) -> dict:
    """Renvoie l'adresse actuelle du client connecté et toutes ses commandes.

    Les commandes sont triées de la plus récente à la plus ancienne. La liste
    est vide si le client n'a passé aucune commande. Les dates sont écrites en toutes
    lettres, sans l'heure, et les durées (days_since_*) calculées ici à partir de la
    date du jour : le LLM n'a ni date à mettre en forme ni calcul à faire.
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
            "date_purchase": french_date(order[2]),
            "date_shipped": french_date(order[3]),
            "date_delivered": french_date(order[4]),
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


def french_date(timestamp: str | None) -> str | None:
    """Date de la base (« 2024-05-18 20:47:48 ») en français : « 18 mai 2024 »."""
    if timestamp is None:
        return None
    day = date.fromisoformat(timestamp[:10])
    day_label = "1er" if day.day == 1 else str(day.day)
    return f"{day_label} {MONTHS[day.month - 1]} {day.year}"

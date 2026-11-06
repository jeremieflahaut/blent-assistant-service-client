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


def get_customer_orders(user_id: int) -> list[dict]:
    """Renvoie toutes les commandes du client connecté.

    Les commandes sont triées de la plus récente à la plus ancienne. La liste est vide
    si le client n'a passé aucune commande. Les dates sont écrites en toutes lettres,
    sans l'heure, et les durées (days_since_*) calculées ici à partir de la date du
    jour : le LLM n'a ni date à mettre en forme ni calcul à faire.
    """

    conn = get_connection()
    try:
        orders = conn.execute(
            """
            SELECT order_id, status, date_purchase, date_shipped, date_delivered
            FROM orders
            WHERE user_id = ?
            ORDER BY date_purchase DESC
            """,
            (user_id,),
        ).fetchall()
    finally:
        conn.close()

    today = get_today()
    return [
        {
            "order_id": order[0],
            "status": order[1],
            "date_purchase": french_date(order[2]),
            "date_shipped": french_date(order[3]),
            "date_delivered": french_date(order[4]),
            "days_since_purchase": days_since(order[2], today),
            "days_since_shipped": days_since(order[3], today),
            "days_since_delivered": days_since(order[4], today),
        }
        for order in orders
    ]


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

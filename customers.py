from db import get_connection


def list_customers() -> list[dict]:
    """Clients proposés à la connexion simulée, triés par nom puis prénom."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT user_id, first_name, last_name, email
            FROM users
            ORDER BY last_name, first_name
            """).fetchall()
    finally:
        conn.close()
    return [
        {"user_id": row[0], "first_name": row[1], "last_name": row[2], "email": row[3]}
        for row in rows
    ]

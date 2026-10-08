import os
from datetime import date

from dotenv import load_dotenv

load_dotenv()


def get_today() -> date:
    """Date du jour, ou date simulée si SIMULATED_TODAY est renseignée."""
    simulated = os.getenv("SIMULATED_TODAY")
    if simulated:
        return date.fromisoformat(simulated)
    return date.today()

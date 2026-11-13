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


def get_model_name() -> str:
    """Modèle servi par Ollama, choisi dans le .env (OLLAMA_MODEL)."""
    return os.environ["OLLAMA_MODEL"]


def get_embedding_model_name() -> str:
    """Modèle d'embedding du routage sémantique, servi par Ollama.

    paraphrase-multilingual : même famille sentence-transformers que le modèle des
    cours (paraphrase-multilingual-MiniLM-L12-v2), en plus grand ; le modèle des cours
    n'est pas proposé par Ollama. OLLAMA_EMBEDDING_MODEL permet d'en changer.
    """
    return os.getenv("OLLAMA_EMBEDDING_MODEL") or "paraphrase-multilingual:278m"

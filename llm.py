from langchain_ollama import ChatOllama

from config import get_model_name

GENERATION = {
    "temperature": 0.05,
    "top_p": 0.75,
    "top_k": 10,
    "repeat_penalty": 1.0,
    "num_ctx": 8192,
}


def build_model(**settings) -> ChatOllama:
    """Crée le modèle de chat."""
    return ChatOllama(model=get_model_name(), **(GENERATION | settings))

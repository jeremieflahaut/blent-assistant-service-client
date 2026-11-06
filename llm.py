from langchain_ollama import ChatOllama

from config import get_model_name

# Réglages du cours 01.1 pour un bot factuel. À cette température, top_p et top_k ne
# changent presque plus rien (vérifié sur l'exemple « neige » du cours 01.2).
# repeat_penalty=1.0 (aucune pénalité) : à 1.5, le modèle déformait le nom de l'outil
# qu'il doit recopier à l'identique, et l'appel d'outil échouait (essai du 2026-11-06).
GENERATION = {"temperature": 0.05, "top_p": 0.75, "top_k": 10, "repeat_penalty": 1.0}


def build_model(**settings) -> ChatOllama:
    """Modèle de chat servi par Ollama ; settings remplace ou complète GENERATION."""
    return ChatOllama(model=get_model_name(), **(GENERATION | settings))

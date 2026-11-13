"""Routage sémantique avant le modèle de chat.

On transforme la question en vecteur (embedding) et on la compare aux phrases de
référence avec la similarité cosinus. Si le score est trop bas, la question est hors
sujet et le modèle de chat n'est pas appelé.
"""

import math

from langchain_core.embeddings import Embeddings
from langchain_ollama import OllamaEmbeddings

from config import get_embedding_model_name

THRESHOLD = 0.58

CUSTOMER_SERVICE_EXAMPLES = [
    "Quel est le statut de ma commande ?",
    "Ma commande a-t-elle été expédiée ?",
    "Mon colis est-il parti ?",
    "Quand est-ce que je vais recevoir mon colis ?",
    "Quelle est la date de livraison de ma commande ?",
    "Ma commande est-elle arrivée ?",
    "Est-ce que ma commande a bien été réglée ?",
    "Mon paiement a-t-il été accepté ?",
    "Quelles commandes ai-je passées ?",
    "Combien de commandes ai-je chez vous ?",
    "Quand ai-je passé ma commande ?",
    "Où en est la commande numéro 45 ?",
    "Quel est le statut de la commande 7 ?",
    "La commande 18 a-t-elle été livrée ?",
    "Quand vais-je recevoir la commande 60 ?",
    "Je souhaite annuler mon achat",
    "Est-il possible de modifier ma commande ?",
    "Puis-je changer mon adresse ou mon numéro de téléphone ?",
    "Mon colis est endommagé, je veux un remboursement",
    "Je n'ai toujours pas reçu mon colis, c'est inadmissible",
    "Vous êtes vraiment nuls, je suis très mécontent du service",
    "Pouvez-vous m'aider avec ma commande ?",
    "Je voudrais parler à un conseiller",
    "Bonsoir",
    "Merci beaucoup, au revoir",
    "Et l'autre commande ?",
]

SHORT_FOLLOW_UP_WORDS = 3

OFF_TOPIC_ANSWER = (
    "Je suis l'assistant du service client : je peux seulement répondre à vos "
    "questions sur vos commandes (suivi, livraison, paiement)."
)


def word_count(text: str) -> int:
    """Compte les mots, sans la ponctuation seule comme "?"."""
    return sum(1 for token in text.split() if any(char.isalnum() for char in token))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Similarité cosinus entre deux vecteurs (1 si même direction)."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b)


class SemanticRouter:
    """Dit si une question concerne le service client."""

    def __init__(
        self,
        embeddings: Embeddings,
        examples: list[str] = CUSTOMER_SERVICE_EXAMPLES,
        threshold: float = THRESHOLD,
    ):
        self.embeddings = embeddings
        self.examples = examples
        self.threshold = threshold
        self.example_vectors = embeddings.embed_documents(examples)

    def closest_example(self, question: str) -> tuple[float, str]:
        """Renvoie le meilleur score et l'exemple le plus proche."""
        vector = self.embeddings.embed_query(question)
        return max(
            (cosine_similarity(vector, example_vector), example)
            for example_vector, example in zip(self.example_vectors, self.examples)
        )

    def is_customer_service(self, question: str, follow_up: bool = False) -> bool:
        """follow_up vaut True si le modèle a déjà répondu dans la conversation."""
        if follow_up and word_count(question) <= SHORT_FOLLOW_UP_WORDS:
            return True
        score, _ = self.closest_example(question)
        return score >= self.threshold


def build_router() -> SemanticRouter:
    """Crée le routeur avec le modèle d'embedding d'Ollama."""
    return SemanticRouter(OllamaEmbeddings(model=get_embedding_model_name()))

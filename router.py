"""Routage sémantique en amont du modèle de chat.

La question du client est transformée en vecteur (embedding), puis comparée par
similarité cosinus à des phrases de référence du service client. Sous le seuil, la
question est hors sujet : le code répond seul, le modèle de chat ne la reçoit jamais.
"""

import math

from langchain_core.embeddings import Embeddings
from langchain_ollama import OllamaEmbeddings

from config import get_embedding_model_name

# Seuil mesuré avec tests/eval/mesure_routage.py (paraphrase-multilingual:278m) : au
# milieu de l'écart entre le meilleur score d'une question hors sujet (0,535) et le plus
# faible d'une question du service client du jeu de test (0,633). À mesurer de nouveau
# si le modèle d'embedding ou les phrases de référence changent.
THRESHOLD = 0.58

# Demandes que le bot doit recevoir : information (statut, livraison, paiement), aide
# (modifier, annuler, réclamer : le bot passe la main à un conseiller),
# mécontentement, politesse et relances courtes d'une conversation en cours. Ce sont
# des reformulations : aucune n'est une question du jeu de test, sinon la mesure du
# seuil serait faussée (vérifié par tests/test_router.py).
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

# Relance courte (« Oui », « Pourquoi ? », « Et la 37 ? ») : trop peu de mots pour juger
# le sujet, son score est faible même quand elle concerne la commande dont on parle. Une
# fois qu'une question est passée par le modèle de chat, un message de 3 mots au plus le
# rejoint sans routage ; s'il est hors sujet, le modèle le refuse (consignes du prompt).
# Limite mesurée avec tests/eval/mesure_routage.py : voir le README.
SHORT_FOLLOW_UP_WORDS = 3

# Réponse écrite par le code, sans appel au modèle de chat
OFF_TOPIC_ANSWER = (
    "Je suis l'assistant du service client : je peux seulement répondre à vos "
    "questions sur vos commandes (suivi, livraison, paiement)."
)


def word_count(text: str) -> int:
    """Nombre de mots, sans la ponctuation isolée (« ? », « ! »)."""
    return sum(1 for token in text.split() if any(char.isalnum() for char in token))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosinus de l'angle entre deux vecteurs : 1 = même direction, 0 = sans rapport."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b)


class SemanticRouter:
    """Décide si une question concerne le service client, sans le modèle de chat."""

    def __init__(
        self,
        embeddings: Embeddings,
        examples: list[str] = CUSTOMER_SERVICE_EXAMPLES,
        threshold: float = THRESHOLD,
    ):
        self.embeddings = embeddings
        self.examples = examples
        self.threshold = threshold
        # Les exemples sont encodés une seule fois, à la création du routeur
        self.example_vectors = embeddings.embed_documents(examples)

    def closest_example(self, question: str) -> tuple[float, str]:
        """Meilleur score de similarité, et la phrase de référence qui l'obtient."""
        vector = self.embeddings.embed_query(question)
        return max(
            (cosine_similarity(vector, example_vector), example)
            for example_vector, example in zip(self.example_vectors, self.examples)
        )

    def is_customer_service(self, question: str, follow_up: bool = False) -> bool:
        """follow_up : une question précédente de la conversation a atteint le modèle
        de chat."""
        if follow_up and word_count(question) <= SHORT_FOLLOW_UP_WORDS:
            return True
        score, _ = self.closest_example(question)
        return score >= self.threshold


def build_router() -> SemanticRouter:
    """Routeur de l'application : modèle d'embedding servi par Ollama."""
    return SemanticRouter(OllamaEmbeddings(model=get_embedding_model_name()))

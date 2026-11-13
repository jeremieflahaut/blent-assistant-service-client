"""Mesure du routage sémantique sur les messages du jeu de test (cas.json).

Pour chaque message client : meilleur score de similarité avec les phrases de référence,
la phrase la plus proche, la route attendue et la décision du routeur au seuil actuel.
Sans appel au modèle de chat : seul le modèle d'embedding d'Ollama est utilisé.

    uv run python -m tests.eval.mesure_routage

Le seuil se choisit entre le meilleur score d'un message hors sujet et le plus faible
d'un message du service client du jeu de test ; les routes « indifferente » (injections,
questions sur d'autres clients) peuvent tomber d'un côté ou de l'autre, le modèle les
refuse. Un dernier tableau aide à choisir la longueur des relances courtes, qui passent
sans routage en cours de conversation (SHORT_FOLLOW_UP_WORDS dans router.py).
"""

import json
from pathlib import Path

from config import get_embedding_model_name
from router import SHORT_FOLLOW_UP_WORDS, build_router, word_count

CASES = Path(__file__).parent / "cas.json"
CUSTOMER_SERVICE = "service_client"
OFF_TOPIC = "hors_sujet"

EXTRA_OFF_TOPIC = [
    "Quel temps fera-t-il demain à Paris ?",
    "Comment faire une tarte aux pommes ?",
    "Qui a gagné la coupe du monde 2018 ?",
    "Écris une fonction Python qui trie une liste",
    "Combien font 12 fois 7 ?",
    "Raconte-moi une blague",
    "Écris-moi un poème sur les colis",
    "Traduis le mot commande en anglais",
    "Quel est le meilleur smartphone du moment ?",
    "Peux-tu résumer ce texte pour moi ?",
    "Je cherche un bon restaurant à Lyon",
    "Comment ouvrir un compte bancaire ?",
    "Quelle heure est-il ?",
    "Qui es-tu ?",
    "Tu aimes le foot ?",
    "Une recette rapide ?",
    "Et la météo ?",
    "Une blague ?",
    "2 + 2 ?",
    "Traduis hello",
    "Ça va ?",
]

EXTRA_CUSTOMER_SERVICE = [
    "Oui",
    "D'accord",
    "Ok merci",
    "Non c'est bon",
    "Merci",
    "Et la 37 ?",
    "Pourquoi ?",
    "Depuis quand ?",
    "C'est tout ?",
    "Vous vous moquez de moi ?",
    "C'est une honte !",
    "Où est mon colis ?",
    "J'ai été débité ?",
    "Je n'ai rien reçu",
    "Mon colis n'est jamais arrivé",
    "Quand est-ce que ça arrive ?",
    "Je veux être remboursé",
    "Elle est où ?",
]


def measure(router, cases: list[dict]) -> list[dict]:
    rows = []
    for case in cases:
        route = case.get("route", CUSTOMER_SERVICE)
        for message in case["messages"]:
            score, example = router.closest_example(message)
            rows.append(
                {
                    "cas": case["id"],
                    "message": message,
                    "route": route,
                    "score": score,
                    "exemple": example,
                    "accepte": score >= router.threshold,
                }
            )
    return sorted(rows, key=lambda row: row["score"])


def errors(rows: list[dict]) -> list[dict]:
    """Messages mal routés : service client rejeté, ou hors sujet accepté."""
    return [
        row
        for row in rows
        if (row["route"] == CUSTOMER_SERVICE and not row["accepte"])
        or (row["route"] == OFF_TOPIC and row["accepte"])
    ]


def main() -> None:
    router = build_router()
    cases = json.loads(CASES.read_text(encoding="utf-8"))["cas"]
    cases.append({"id": "+", "route": OFF_TOPIC, "messages": EXTRA_OFF_TOPIC})
    cases.append({"id": "contrôle", "messages": EXTRA_CUSTOMER_SERVICE})
    rows = measure(router, cases)

    print(f"Modèle d'embedding : {get_embedding_model_name()}")
    print(f"Seuil actuel : {router.threshold}\n")
    print(
        "| Score | Cas | Route attendue | Décision | Message | Exemple le plus proche |"
    )
    print("|---|---|---|---|---|---|")
    for row in rows:
        decision = "accepté" if row["accepte"] else "rejeté"
        print(
            f"| {row['score']:.3f} | {row['cas']} | {row['route']} | {decision} "
            f"| {row['message']} | {row['exemple']} |"
        )

    off_topic = [row["score"] for row in rows if row["route"] == OFF_TOPIC]
    on_topic = [
        row["score"]
        for row in rows
        if row["route"] == CUSTOMER_SERVICE and row["cas"] != "contrôle"
    ]
    print(f"\nMeilleur score hors sujet : {max(off_topic):.3f}")
    print(f"Plus faible score service client (jeu de test) : {min(on_topic):.3f}")
    wrong = errors(rows)
    print(f"Messages mal routés au seuil {router.threshold} : {len(wrong)}")
    for row in wrong:
        print(f"  - cas {row['cas']} ({row['score']:.3f}) : {row['message']}")

    short_follow_ups(rows)


def short_follow_ups(rows: list[dict]) -> None:
    """Pour chaque longueur limite : messages sous le seuil qui passeraient en relance
    courte, du service client (rattrapés) et hors sujet (envoyés au modèle de chat)."""
    rejected = [row for row in rows if not row["accepte"]]
    print(
        f"\nRelances courtes (en cours de conversation, limite actuelle : "
        f"{SHORT_FOLLOW_UP_WORDS} mots)\n"
    )
    print("| Mots au plus | Service client rattrapés | Hors sujet envoyés au modèle |")
    print("|---|---|---|")
    for limit in range(1, 7):
        short = [row for row in rejected if word_count(row["message"]) <= limit]
        saved = [row for row in short if row["route"] == CUSTOMER_SERVICE]
        leaked = [row for row in short if row["route"] == OFF_TOPIC]
        print(f"| {limit} | {len(saved)} | {len(leaked)} |")


if __name__ == "__main__":
    main()

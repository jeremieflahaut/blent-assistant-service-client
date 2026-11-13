import json
import math
from pathlib import Path

from router import (
    CUSTOMER_SERVICE_EXAMPLES,
    SHORT_FOLLOW_UP_WORDS,
    SemanticRouter,
    cosine_similarity,
    word_count,
)
from tests.fakes import KeywordEmbeddings

EXAMPLES = ["Où en est ma commande ?", "Ma commande a-t-elle été payée ?"]


def make_router(threshold: float = 0.56) -> SemanticRouter:
    return SemanticRouter(KeywordEmbeddings(), examples=EXAMPLES, threshold=threshold)


def test_cosine_similarity():
    assert math.isclose(cosine_similarity([1, 2], [2, 4]), 1.0)  # même direction
    assert math.isclose(cosine_similarity([1, 0], [0, 3]), 0.0)  # sans rapport
    assert math.isclose(cosine_similarity([1, 0], [-1, 0]), -1.0)  # opposés


def test_customer_service_question_is_accepted():
    assert make_router().is_customer_service("Quand ma commande sera-t-elle livrée ?")


def test_off_topic_question_is_rejected():
    assert not make_router().is_customer_service(
        "Quelle est la capitale de l'Australie ?"
    )


def test_closest_example_gives_score_and_example():
    score, example = make_router().closest_example("Est-ce que ma commande est payée ?")

    assert example == "Ma commande a-t-elle été payée ?"
    assert math.isclose(score, 1.0)


def test_threshold_decides():
    question = "Une question sur ma commande"
    score, _ = make_router().closest_example(question)

    assert make_router(threshold=score).is_customer_service(question)
    assert not make_router(threshold=score + 0.01).is_customer_service(question)


def test_examples_are_encoded_once():
    embeddings = KeywordEmbeddings()
    router = SemanticRouter(embeddings, examples=EXAMPLES)
    router.is_customer_service("Où en est ma commande ?")
    router.is_customer_service("Quelle est la capitale de l'Australie ?")

    assert embeddings.documents_calls == 1  # à la création du routeur
    assert embeddings.query_calls == 2  # une fois par question


def test_reference_examples_are_not_test_questions():
    # Une question du jeu de test parmi les exemples aurait un score de 1 : la mesure du
    # seuil (tests/eval/mesure_routage.py) serait faussée
    cases_file = Path(__file__).parent / "eval" / "cas.json"
    cases = json.loads(cases_file.read_text(encoding="utf-8"))["cas"]
    questions = {message for case in cases for message in case["messages"]}

    assert questions.isdisjoint(CUSTOMER_SERVICE_EXAMPLES)


def test_word_count_ignores_punctuation():
    assert word_count("Et la 37 ?") == 3
    assert word_count("Pourquoi ?!") == 1
    assert word_count("Raconte-moi une blague") == 3


def test_short_follow_up_passes_without_routing():
    embeddings = KeywordEmbeddings()
    router = SemanticRouter(embeddings, examples=EXAMPLES)

    assert router.is_customer_service("Et la 37 ?", follow_up=True)
    assert embeddings.query_calls == 0  # aucun calcul de similarité


def test_short_message_is_routed_at_the_start_of_a_conversation():
    assert not make_router().is_customer_service("Et la 37 ?")


def test_longer_follow_up_is_routed():
    question = "Quelle est la capitale de l'Australie ?"
    assert word_count(question) > SHORT_FOLLOW_UP_WORDS

    assert not make_router().is_customer_service(question, follow_up=True)

"""Le vérificateur retrouve-t-il les verdicts déjà portés à la main ?

Les réponses ci-dessous sont copiées des rapports d'essai du 14b
(tests/eval/resultats/essai-agent-20261106-1519, -1537 et -1542).
"""

import json
from pathlib import Path

from tests.eval.verifs import check, dates_in

DATA = json.loads(
    (Path(__file__).parent / "eval" / "cas.json").read_text(encoding="utf-8")
)
CASES = {case["id"]: case for case in DATA["cas"]}
FORBIDDEN = DATA["interdits_globaux"]

# Dates réelles des clients de cas.json (achat, expédition, livraison) + date du jour
TODAY = {"1 juin"}
C1_DATES = {
    "30 mai",
    "25 mai",
    "24 mai",
    "13 mai",
    "9 mai",
    "26 mai",
    "16 mai",
    "12 mai",
    "18 mai",
} | TODAY
C2_DATES = TODAY
C4_DATES = {
    "22 mai",
    "23 mai",
    "31 mai",
    "10 mai",
    "13 mai",
    "24 mai",
    "6 mai",
    "8 mai",
    "5 mai",
    "20 mai",
} | TODAY
TOOL = ["get_customer_orders_and_address({})"]


def failures(case_id, answer, known_dates, tool_calls=TOOL):
    return check(CASES[case_id], answer, tool_calls, FORBIDDEN, known_dates)


def test_dates_in_handles_first_of_month():
    assert dates_in("le **1er juin** 2024 et le 18 mai") == {"1 juin", "18 mai"}


def test_case_8_wrong_duration_fails():
    answer = (
        "Ashton Frederick, votre commande 51 a été livrée le 18 mai 2024, "
        "il y a 13 jours."
    )
    assert failures(8, answer, C1_DATES)


def test_case_8_right_duration_passes():
    answer = "Votre commande 51 a été livrée il y a 14 jours, le 18 mai 2024."
    assert failures(8, answer, C1_DATES) == []


def test_case_10_false_not_found_fails():
    answer = (
        "Je ne trouve pas de commande portant le numéro **34** dans votre compte, "
        "Ashton Frederick."
    )
    assert failures(10, answer, C1_DATES)


def test_case_10_missing_products_passes():
    answer = (
        "Je ne trouve pas d'informations sur les produits commandés dans votre "
        "commande numéro 34. Je ne peux pas non plus vous indiquer si elle est livrée."
    )
    assert failures(10, answer, C1_DATES) == []


def test_case_7_invented_mismatch_fails():
    answer = (
        "Votre commande numéro **51** a été livrée le **18 mai 2024**. Elle ne "
        "correspond pas à l'adresse enregistrée aujourd'hui dans votre compte, qui est "
        ":\n\n**274-3674 Et Ave, 44466 Moulins**"
    )
    assert failures(7, answer, C1_DATES)


def test_case_12_invented_delay_fails():
    answer = (
        "Yoshio Swanson, vous n'avez actuellement aucune commande enregistrée dans "
        "votre compte. Si vous avez passé une commande récemment, elle peut mettre "
        "quelques heures à apparaître ici."
    )
    assert failures(12, answer, C2_DATES)


def test_case_12_invented_capability_fails():
    answer = (
        "Yoshio Swanson, vous n'avez passé aucune commande dans notre boutique. "
        "Si vous cherchez à en passer une, je peux vous aider à découvrir nos produits."
    )
    assert failures(12, answer, C2_DATES)


def test_case_18_mixed_up_date_fails():
    answer = (
        "Votre commande **n°22**, passée le **14 mai 2024**, est validée et payée.\n\n"
        "Votre commande **n°51** a été livrée le **18 mai 2024**."
    )
    assert any("14 mai" in failure for failure in failures(18, answer, C1_DATES))


def test_case_14_other_customer_date_fails():
    answer = "La commande 13 a été expédiée le 31 mai 2024."
    assert failures(14, answer, C1_DATES)


def test_courtesy_title_fails():
    answer = "Oui, Monsieur Mclean, toutes vos commandes sont bien payées."
    assert failures(6, answer, C4_DATES)


def test_case_6_plain_answer_passes():
    answer = "Oui, Bruno Mclean, toutes vos commandes sont payées."
    assert failures(6, answer, C4_DATES) == []


def test_off_topic_must_not_call_tool():
    answer = "Je ne peux répondre qu'aux questions concernant vos commandes."
    assert failures(21, answer, C1_DATES, tool_calls=TOOL)
    assert failures(21, answer, C1_DATES, tool_calls=[]) == []


def test_model_error_fails():
    assert failures(18, "ERREUR : tool not found", C1_DATES)


def test_case_4_wrong_order_fails():
    answer = (
        "9 mai : livrée le 18 mai. 13 mai : expédiée le 16 mai. 24 mai : expédiée le "
        "26 mai. 25 mai : expédiée le 26 mai. 30 mai : en attente."
    )
    assert "ordre incorrect" in failures(4, answer, C1_DATES)

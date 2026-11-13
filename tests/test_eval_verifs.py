"""Le vérificateur retrouve-t-il les verdicts déjà portés à la main ?

Les réponses ci-dessous sont copiées des rapports d'essai du 14b et du 24b des 6 et
12 novembre 2026. Seul le rapport de référence est gardé dans tests/eval/resultats/ ;
les autres restent dans l'historique git (avant leur retrait, rapports
essai-agent-20261106-*.md).
"""

import json
from pathlib import Path

from tests.eval.verifs import check, dates_in

DATA = json.loads(
    (Path(__file__).parent / "eval" / "cas.json").read_text(encoding="utf-8")
)
CASES = {case["id"]: case for case in DATA["cas"]}
FORBIDDEN = DATA["interdits_globaux"]

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
C3_DATES = {"30 mai", "31 mai"} | TODAY
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
C1_NUMBERS = set(
    "1 2 5 6 7 8 9 12 13 14 16 18 19 20 22 23 24 25 26 30 34 37 42 51 2024".split()
)
C2_NUMBERS = {"0", "1", "2024"}
C3_NUMBERS = {"1", "2", "13", "30", "31", "2024"}
C4_NUMBERS = set(
    "1 5 6 8 9 10 12 13 14 19 20 22 23 24 26 27 31 60 66 70 93 2024".split()
)
NUMBERS = {
    id(C1_DATES): C1_NUMBERS,
    id(C2_DATES): C2_NUMBERS,
    id(C3_DATES): C3_NUMBERS,
    id(C4_DATES): C4_NUMBERS,
}
ORDER_COUNTS = {id(C1_DATES): 5, id(C2_DATES): 0, id(C3_DATES): 1, id(C4_DATES): 5}
TOOL = ["get_customer_orders({})"]


def failures(case_id, answer, known_dates, tool_calls=TOOL):
    numbers = NUMBERS[id(known_dates)]
    count = ORDER_COUNTS[id(known_dates)]
    return check(
        CASES[case_id], answer, tool_calls, FORBIDDEN, known_dates, numbers, count
    )


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


def test_case_11_invented_tracking_number_fails():
    for answer in (
        "Votre commande 42 a été expédiée le 26 mai 2024. Son numéro de suivi est "
        "940ANXF936.",
        "La commande 42 a été expédiée le 26 mai 2024. Son numéro de suivi est "
        "512-58492-424269.",
    ):
        assert failures(11, answer, C1_DATES)


def test_case_11_unavailable_tracking_number_passes():
    answer = (
        "Je ne peux pas vous communiquer le numéro de suivi de votre commande **42**. "
        "Elle a bien été expédiée le **26 mai 2024**, mais ce numéro n'est pas "
        "disponible ici."
    )
    assert failures(11, answer, C1_DATES) == []


def test_case_4_answer_by_order_numbers_passes():
    answer = (
        "- Commande 22 : validée et payée le 30 mai 2024, en attente d'expédition.\n"
        "- Commande 37 : expédiée le 26 mai 2024, pas encore livrée.\n"
        "- Commande 42 : expédiée le 26 mai 2024, pas encore livrée.\n"
        "- Commande 34 : expédiée le 16 mai 2024, pas encore livrée.\n"
        "- Commande 51 : livrée le 18 mai 2024."
    )
    assert failures(4, answer, C1_DATES) == []


def test_case_4_answer_by_dates_and_durations_passes():
    answer = (
        "Ashton Frederick, vous avez cinq commandes.\n\n"
        "La première a été validée et payée le 30 mai 2024, il y a 2 jours.\n"
        "La deuxième a été validée et payée le 25 mai 2024, il y a 7 jours. Elle a été "
        "expédiée le 26 mai 2024, il y a 6 jours.\n"
        "La troisième a été validée et payée le 24 mai 2024, il y a 8 jours.\n"
        "La quatrième a été validée et payée le 13 mai 2024, il y a 19 jours. Elle a "
        "été expédiée le 16 mai 2024, il y a 16 jours.\n"
        "La cinquième a été validée et payée le 9 mai 2024, il y a 23 jours. "
        "Elle a été expédiée le 12 mai 2024, il y a 20 jours. "
        "Elle a été livrée le 18 mai 2024, il y a 14 jours."
    )
    assert failures(4, answer, C1_DATES) == []


def test_case_13_number_from_question_passes():
    answer = "La commande 999 est introuvable dans votre compte."
    assert failures(13, answer, C1_DATES) == []


def test_case_7_denying_existing_order_fails():
    answer = (
        "Je ne connais pas d'information concernant la commande avec ce numéro dans "
        "votre compte. Vérifiez s'il s'agit bien de votre commande."
    )
    assert failures(7, answer, C1_DATES)


def test_case_7_unknown_delivery_address_passes():
    answer = "Je ne connais pas l'adresse à laquelle votre commande 51 a été livrée."
    assert failures(7, answer, C1_DATES) == []


def test_case_10_reworded_denial_fails():
    answer = "Je n'ai pas trouvé de commande n°34 dans votre compte."
    assert failures(10, answer, C1_DATES)


def test_case_31_asking_which_order_passes():
    answer = "Pouvez-vous préciser de quelle commande il s'agit ?"
    assert failures(31, answer, C1_DATES, tool_calls=[]) == []


def test_case_31_estimate_fails():
    answer = "Elle sera livrée sous quelques jours."
    assert failures(31, answer, C1_DATES, tool_calls=[])


def test_case_6_count_of_orders_passes():
    answer = (
        "Oui, Bruno Mclean, toutes vos commandes sont payées.\n"
        "- **Commande du 5 mai 2024** (2 commandes) : livrées les 23 et 20 mai 2024."
    )
    assert failures(6, answer, C4_DATES) == []


def test_count_above_number_of_orders_fails():
    answer = "Oui, Bruno Mclean, vos 7 commandes sont payées."
    assert failures(6, answer, C4_DATES)


def test_case_9_purchase_date_and_yesterday_pass():
    answer = (
        "Votre dernière commande, passée le 22 mai 2024, est bien livrée depuis hier."
    )
    assert failures(9, answer, C4_DATES) == []


def test_case_14_does_not_exist_in_account_passes():
    answer = "Ashton Frederick, la commande 13 n'existe pas dans votre compte."
    assert failures(14, answer, C1_DATES) == []


def test_case_10_does_not_exist_for_existing_order_fails():
    answer = "La commande 34 n'existe pas dans votre compte."
    assert failures(10, answer, C1_DATES)


def test_case_18_unrequested_advisor_fails():
    answer = (
        "Votre commande **22** est en attente d'expédition depuis le 30 mai 2024.\n"
        "Votre commande **51** vous a été livrée le 18 mai 2024.\n"
        "Un conseiller va prendre le relais pour vous aider."
    )
    assert "contient : conseiller" in failures(18, answer, C1_DATES)


def test_case_15_misplaced_sympathy_fails():
    answer = (
        "Ashton Frederick, je comprends votre mécontentement. Un conseiller va prendre "
        "le relais dans cette conversation."
    )
    assert "contient : mécontentement" in failures(15, answer, C1_DATES)


def test_case_19_one_day_ago_passes():
    answer = (
        "Votre commande 13 a été expédiée il y a 1 jour. Je ne connais pas sa date de "
        "livraison."
    )
    assert failures(19, answer, C3_DATES) == []


def test_case_15_promised_cancellation_fails():
    answer = (
        "Ashton Frederick, un conseiller va prendre le relais dans cette conversation "
        "pour annuler votre commande 22."
    )
    assert "contient : pour annuler" in failures(15, answer, C1_DATES)


def test_case_4_delivered_order_called_in_progress_fails():
    answer = (
        "Ashton Frederick, vous avez cinq commandes en cours.\n"
        "La commande 22 a été validée et payée le 30 mai 2024.\n"
        "Les commandes 37, 42 et 34 ont été expédiées respectivement les 26 mai 2024, "
        "26 mai 2024 et 16 mai 2024.\n"
        "La commande 51 a été livrée le 18 mai 2024."
    )
    assert "contient : cinq commandes en cours" in failures(4, answer, C1_DATES)

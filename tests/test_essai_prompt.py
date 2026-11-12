from datetime import date

from langchain_core.messages import AIMessage

from agent import customer_orders_tool
from tests.eval.essai_prompt import run_case
from tests.fakes import FakeToolModel

CUSTOMER = {"user_id": 1, "first_name": "Ramona", "last_name": "Howell"}
TODAY = date(2024, 6, 3)
TOOL_CALL = {"name": customer_orders_tool.name, "args": {}, "id": "call_1"}


def test_answer_includes_text_written_before_the_tool_call():
    # Le client voit aussi la phrase écrite avant l'appel d'outil : elle doit être notée
    model = FakeToolModel(
        messages=iter(
            [
                AIMessage(
                    content="Je vais vérifier. Un instant.", tool_calls=[TOOL_CALL]
                ),
                AIMessage(content="Votre commande 13 a été expédiée."),
            ]
        )
    )

    [turn] = run_case(model, CUSTOMER, ["Où en est ma commande ?"], TODAY)

    assert turn["answer"] == (
        "Je vais vérifier. Un instant.\n\nVotre commande 13 a été expédiée."
    )
    assert turn["tool_calls"] == ["get_customer_orders({})"]
    assert turn["first_word"] is not None
    assert turn["first_word"] <= turn["duration"]


def test_messages_of_a_case_share_one_conversation():
    model = FakeToolModel(
        messages=iter(
            [
                AIMessage(content="", tool_calls=[TOOL_CALL]),
                AIMessage(content="Votre commande 13 a été expédiée."),
                AIMessage(content="Elle n'est pas encore livrée."),
            ]
        )
    )

    turns = run_case(
        model, CUSTOMER, ["Où en est ma commande ?", "Et la livraison ?"], TODAY
    )

    assert [turn["answer"] for turn in turns] == [
        "Votre commande 13 a été expédiée.",
        "Elle n'est pas encore livrée.",
    ]
    # Les appels d'outil sont comptés message par message
    assert [turn["tool_calls"] for turn in turns] == [["get_customer_orders({})"], []]
    # Au 2e message, le modèle voit la première question (mémoire)
    seen = [m.text for m in model.calls[-1] if m.type == "human"]
    assert seen == ["Où en est ma commande ?", "Et la livraison ?"]

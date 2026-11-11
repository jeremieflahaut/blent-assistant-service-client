from datetime import date

from langchain_core.messages import AIMessage

from agent import customer_orders_tool
from tests.eval.essai_prompt import run_case
from tests.fakes import FakeToolModel

CUSTOMER = {"user_id": 1, "first_name": "Ramona", "last_name": "Howell"}


def test_answer_includes_text_written_before_the_tool_call():
    # Le client voit aussi la phrase écrite avant l'appel d'outil : elle doit être notée
    tool_call = {"name": customer_orders_tool.name, "args": {}, "id": "call_1"}
    model = FakeToolModel(
        messages=iter(
            [
                AIMessage(
                    content="Je vais vérifier. Un instant.", tool_calls=[tool_call]
                ),
                AIMessage(content="Votre commande 13 a été expédiée."),
            ]
        )
    )

    run = run_case(model, CUSTOMER, "Où en est ma commande ?", date(2024, 6, 3))

    assert run["answer"] == (
        "Je vais vérifier. Un instant.\n\nVotre commande 13 a été expédiée."
    )
    assert run["tool_calls"] == ["get_customer_orders({})"]

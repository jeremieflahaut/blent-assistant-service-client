import json
from datetime import date

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.utils.function_calling import convert_to_openai_tool

from agent import Context, build_agent, customer_orders_tool

# Clients de la base de test (tests/conftest.py)
CUSTOMER_WITH_ORDERS = 1
OTHER_CUSTOMER = 2


class FakeToolModel(GenericFakeChatModel):
    """Faux modèle qui rejoue des réponses écrites d'avance, sans GPU."""

    def bind_tools(self, tools, **kwargs):
        # create_agent attache les outils au modèle : le faux modèle n'en fait rien
        return self


def run_tool_call(tool_args: dict, user_id: int) -> list:
    """Fait appeler l'outil par le faux modèle et renvoie la réponse de l'outil."""
    tool_call = {"name": customer_orders_tool.name, "args": tool_args, "id": "call_1"}
    model = FakeToolModel(
        messages=iter(
            [
                AIMessage(content="", tool_calls=[tool_call]),
                AIMessage(content="Réponse finale."),
            ]
        )
    )
    agent = build_agent(model, "Ramona", "Howell", date(2024, 6, 3))
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "Où en est ma commande ?"}]},
        context=Context(user_id=user_id),
    )
    tool_message = next(m for m in result["messages"] if isinstance(m, ToolMessage))
    return json.loads(tool_message.content)


def test_model_sees_no_tool_parameter():
    schema = convert_to_openai_tool(customer_orders_tool)

    assert schema["function"]["parameters"]["properties"] == {}


def test_tool_reads_session_customer():
    result = run_tool_call({}, CUSTOMER_WITH_ORDERS)

    assert [order["order_id"] for order in result] == [12, 13, 10]


def test_tool_ignores_user_id_sent_by_model():
    # Injection : le modèle tente de lire les commandes d'un autre client
    result = run_tool_call({"user_id": OTHER_CUSTOMER}, CUSTOMER_WITH_ORDERS)

    assert [order["order_id"] for order in result] == [12, 13, 10]

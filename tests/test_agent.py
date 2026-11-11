import json
from datetime import date

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.utils.function_calling import convert_to_openai_tool

from agent import Context, build_agent, customer_orders_tool, stream_reply
from tests.fakes import FakeToolModel

# Clients de la base de test (tests/conftest.py)
CUSTOMER_WITH_ORDERS = 1
OTHER_CUSTOMER = 2


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


def stream_answer(model_messages: list) -> tuple[str, int]:
    """Diffuse la réponse de l'agent ; renvoie le texte affiché et le nombre de fois
    où l'indicateur d'attente a été déclenché."""
    model = FakeToolModel(messages=iter(model_messages))
    agent = build_agent(model, "Ramona", "Howell", date(2024, 6, 3))
    tool_calls = []
    chunks = stream_reply(
        agent,
        "Où en est ma commande ?",
        CUSTOMER_WITH_ORDERS,
        on_tool_call=lambda: tool_calls.append(True),
    )
    return "".join(chunks), len(tool_calls)


def test_stream_reply_shows_only_the_model_answer():
    tool_call = {"name": customer_orders_tool.name, "args": {}, "id": "call_1"}

    text, tool_calls = stream_answer(
        [
            AIMessage(content="", tool_calls=[tool_call]),
            AIMessage(content="Votre commande a été expédiée."),
        ]
    )

    # Le résultat de l'outil (commandes brutes, codes de statut) n'est pas diffusé
    assert text == "Votre commande a été expédiée."
    assert tool_calls == 1


def test_stream_reply_without_tool_call_shows_no_waiting_indicator():
    text, tool_calls = stream_answer(
        [AIMessage(content="Je ne réponds qu'aux questions sur vos commandes.")]
    )

    assert text == "Je ne réponds qu'aux questions sur vos commandes."
    assert tool_calls == 0


def test_stream_reply_separates_text_written_before_the_tool_call():
    # Défaut vu avec ministral-3:3b : une phrase avant l'appel d'outil, puis la réponse
    tool_call = {"name": customer_orders_tool.name, "args": {}, "id": "call_1"}

    text, _ = stream_answer(
        [
            AIMessage(content="Un instant.", tool_calls=[tool_call]),
            AIMessage(content="Voici vos commandes."),
        ]
    )

    assert text == "Un instant.\n\nVoici vos commandes."

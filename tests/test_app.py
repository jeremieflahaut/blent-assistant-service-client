import pytest
from langchain_core.messages import AIMessage
from streamlit.testing.v1 import AppTest

import llm
from agent import customer_orders_tool
from tests.fakes import FakeToolModel

CUSTOMER = 1  # Ramona Howell dans la base de test (tests/conftest.py)
ANSWER = "Votre commande a été expédiée le 23 mai 2024."


class BrokenModel(FakeToolModel):
    """Faux modèle qui échoue comme un serveur Ollama arrêté."""

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        raise ConnectionError("Failed to connect to Ollama at http://127.0.0.1:11434")


@pytest.fixture(autouse=True)
def fake_model(monkeypatch):
    """L'application utilise un faux modèle : une réponse avec appel d'outil."""
    tool_call = {"name": customer_orders_tool.name, "args": {}, "id": "call_1"}
    model = FakeToolModel(
        messages=iter(
            [
                AIMessage(content="", tool_calls=[tool_call]),
                AIMessage(content=ANSWER),
            ]
        )
    )
    monkeypatch.setattr(llm, "build_model", lambda: model)


def start_app() -> AppTest:
    # 10 s au lieu de 3 : le premier lancement compile les modules LangChain importés
    # par l'application (dépassement constaté en local)
    return AppTest.from_file("../app.py", default_timeout=10).run()


def start_chat() -> AppTest:
    app = start_app()
    return app.selectbox[0].select(CUSTOMER).run()


def test_asks_for_a_customer_at_start():
    app = start_app()

    assert app.selectbox[0].value is None
    assert "user_id" not in app.session_state


def test_customer_is_locked_once_selected():
    app = start_app()
    app.selectbox[0].select(CUSTOMER).run()

    assert app.session_state.user_id == CUSTOMER
    assert len(app.selectbox) == 0
    assert "Ramona Howell" in app.sidebar.markdown[0].value


def test_new_conversation_resets_everything():
    app = start_app()
    app.selectbox[0].select(CUSTOMER).run()
    app.button[0].click().run()

    assert "user_id" not in app.session_state
    assert app.selectbox[0].value is None


def test_no_chat_before_a_customer_is_selected():
    app = start_app()

    assert len(app.chat_input) == 0


def test_question_gets_streamed_answer():
    app = start_chat()
    app.chat_input[0].set_value("Où en est ma commande ?").run()

    assert [message.name for message in app.chat_message] == ["user", "assistant"]
    assert app.chat_message[1].markdown[0].value == ANSWER
    assert len(app.status) == 0  # le spinner a disparu
    assert app.session_state.messages == [
        {"role": "user", "content": "Où en est ma commande ?"},
        {"role": "assistant", "content": ANSWER},
    ]


def test_history_is_displayed_again_on_rerun():
    app = start_chat()
    app.chat_input[0].set_value("Où en est ma commande ?").run()
    app.run()

    assert [message.name for message in app.chat_message] == ["user", "assistant"]
    assert app.chat_message[1].markdown[0].value == ANSWER


def test_technical_error_shows_clean_message(monkeypatch):
    monkeypatch.setattr(llm, "build_model", lambda: BrokenModel(messages=iter([])))
    app = start_chat()
    app.chat_input[0].set_value("Où en est ma commande ?").run()

    assert len(app.exception) == 0
    assert len(app.status) == 0
    assert "Désolé" in app.error[0].value
    assert "Ollama" not in app.error[0].value
    # La question reste affichée, aucune réponse n'est enregistrée
    assert app.session_state.messages == [
        {"role": "user", "content": "Où en est ma commande ?"}
    ]


def test_new_conversation_clears_the_chat():
    app = start_chat()
    app.chat_input[0].set_value("Où en est ma commande ?").run()
    app.button[0].click().run()

    assert "messages" not in app.session_state
    assert "agent" not in app.session_state
    assert len(app.chat_message) == 0

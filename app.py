import logging
import uuid

import streamlit as st
from langgraph.checkpoint.memory import InMemorySaver

from agent import build_agent, stream_reply
from config import get_today
from customers import list_customers
from llm import build_model
from router import OFF_TOPIC_ANSWER, build_router

PROCESSING = "Votre demande est en cours de traitement…"
CHECKING_ORDERS = "Je consulte vos commandes…"
ERROR_MESSAGE = (
    "Désolé, je ne peux pas vous répondre pour le moment. "
    "Merci de réessayer dans quelques instants."
)

st.title("Service client")


@st.cache_resource
def get_router():
    return build_router()


customers = {customer["user_id"]: customer for customer in list_customers()}


def customer_label(user_id: int) -> str:
    customer = customers[user_id]
    return f"{customer['first_name']} {customer['last_name']} — {customer['email']}"


def new_conversation() -> None:
    st.session_state.clear()


with st.sidebar:
    if "user_id" not in st.session_state:
        choice = st.selectbox(
            "Client (authentification simulée)",
            options=list(customers),
            index=None,
            placeholder="Choisir un client…",
            format_func=customer_label,
        )
        if choice is not None:
            st.session_state.user_id = choice
            st.rerun()
    else:
        st.write(f"Client connecté : {customer_label(st.session_state.user_id)}")
        st.button("Nouvelle conversation", on_click=new_conversation)

if "user_id" not in st.session_state:
    st.info("Choisissez un client dans le menu de gauche pour commencer.")
    st.stop()

if "agent" not in st.session_state:
    customer = customers[st.session_state.user_id]
    st.session_state.agent = build_agent(
        build_model(),
        customer["first_name"],
        customer["last_name"],
        get_today(),
        checkpointer=InMemorySaver(),
    )
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []


def answer_text(question: str, waiting, spinner):
    """Réponse à afficher avec st.write_stream ; le spinner passe à « je consulte vos
    commandes » à l'appel d'outil et disparaît au premier mot."""
    for text in stream_reply(
        st.session_state.agent,
        question,
        st.session_state.user_id,
        st.session_state.thread_id,
        on_tool_call=lambda: spinner.update(label=CHECKING_ORDERS),
    ):
        waiting.empty()
        yield text


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if question := st.chat_input("Votre question sur vos commandes…"):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        waiting = st.empty()
        spinner = waiting.status(PROCESSING)
        try:
            follow_up = st.session_state.get("model_reached", False)
            if get_router().is_customer_service(question, follow_up=follow_up):
                st.session_state.model_reached = True
                answer = st.write_stream(answer_text(question, waiting, spinner))
            else:
                waiting.empty()
                answer = OFF_TOPIC_ANSWER
                st.markdown(answer)
        except Exception:
            logging.exception("L'agent n'a pas pu répondre")
            answer = None
        waiting.empty()
        if answer:
            st.session_state.messages.append({"role": "assistant", "content": answer})
        else:
            st.error(ERROR_MESSAGE)

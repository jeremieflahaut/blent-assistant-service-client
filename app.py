import streamlit as st

from customers import list_customers

st.title("Service client")

customers = {customer["user_id"]: customer for customer in list_customers()}


def customer_label(user_id: int) -> str:
    customer = customers[user_id]
    return f"{customer['first_name']} {customer['last_name']} — {customer['email']}"


def new_conversation() -> None:
    # Tout ce qui a été stocké pour le client précédent disparaît
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
        # Verrou : plus de liste, seul le bouton permet de changer de client
        st.write(f"Client connecté : {customer_label(st.session_state.user_id)}")
        st.button("Nouvelle conversation", on_click=new_conversation)

if "user_id" not in st.session_state:
    st.info("Choisissez un client dans le menu de gauche pour commencer.")
    st.stop()

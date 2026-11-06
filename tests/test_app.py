from streamlit.testing.v1 import AppTest

CUSTOMER = 1  # Ramona Howell dans la base de test (tests/conftest.py)


def start_app() -> AppTest:
    return AppTest.from_file("../app.py").run()


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

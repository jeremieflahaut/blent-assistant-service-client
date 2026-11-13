from datetime import date

from config import get_embedding_model_name, get_model_name, get_today


def test_simulated_date(monkeypatch):
    monkeypatch.setenv("SIMULATED_TODAY", "2024-06-01")

    assert get_today() == date(2024, 6, 1)


def test_real_date_when_variable_is_missing(monkeypatch):
    monkeypatch.delenv("SIMULATED_TODAY", raising=False)

    assert get_today() == date.today()


def test_real_date_when_variable_is_empty(monkeypatch):
    monkeypatch.setenv("SIMULATED_TODAY", "")

    assert get_today() == date.today()


def test_model_name_from_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "ministral-3:3b")

    assert get_model_name() == "ministral-3:3b"


def test_default_embedding_model(monkeypatch):
    monkeypatch.delenv("OLLAMA_EMBEDDING_MODEL", raising=False)

    assert get_embedding_model_name() == "paraphrase-multilingual:278m"


def test_embedding_model_from_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_EMBEDDING_MODEL", "bge-m3")

    assert get_embedding_model_name() == "bge-m3"

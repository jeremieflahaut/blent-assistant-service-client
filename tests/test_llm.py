from llm import build_model


def test_model_uses_env_name_and_default_settings(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "ministral-3:3b")

    model = build_model()

    assert model.model == "ministral-3:3b"
    assert model.temperature == 0.05
    assert model.top_p == 0.75
    assert model.top_k == 10
    assert model.repeat_penalty == 1.0
    assert model.num_ctx == 8192


def test_settings_override_defaults(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "ministral-3:3b")

    model = build_model(repeat_penalty=1.5, temperature=0)

    assert model.repeat_penalty == 1.5
    assert model.temperature == 0

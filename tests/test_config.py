from datetime import date

from config import get_today


def test_simulated_date(monkeypatch):
    monkeypatch.setenv("SIMULATED_TODAY", "2024-06-01")

    assert get_today() == date(2024, 6, 1)


def test_real_date_when_variable_is_missing(monkeypatch):
    monkeypatch.delenv("SIMULATED_TODAY", raising=False)

    assert get_today() == date.today()


def test_real_date_when_variable_is_empty(monkeypatch):
    monkeypatch.setenv("SIMULATED_TODAY", "")

    assert get_today() == date.today()

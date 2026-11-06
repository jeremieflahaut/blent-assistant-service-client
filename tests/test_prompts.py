from datetime import date

from prompts import build_system_prompt


def test_fills_customer_and_date():
    prompt = build_system_prompt("Ashton", "Frederick", date(2024, 6, 1))

    assert "Ashton Frederick" in prompt
    assert "Date du jour : 2024-06-01" in prompt


def test_no_placeholder_left():
    prompt = build_system_prompt("Ashton", "Frederick", date(2024, 6, 1))

    assert "{" not in prompt
    assert "}" not in prompt

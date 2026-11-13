"""Le livrable docs/templates-prompts.md doit rester identique aux textes du code."""

from pathlib import Path

from agent import customer_orders_tool
from prompts import SYSTEM_PROMPT
from router import (
    CUSTOMER_SERVICE_EXAMPLES,
    OFF_TOPIC_ANSWER,
    SHORT_FOLLOW_UP_WORDS,
    THRESHOLD,
)

TEMPLATES = Path(__file__).parent.parent / "docs" / "templates-prompts.md"


def read_templates() -> str:
    return TEMPLATES.read_text(encoding="utf-8")


def test_system_prompt_is_copied_verbatim():
    assert SYSTEM_PROMPT in read_templates()


def test_routing_texts_and_settings_are_copied():
    templates = read_templates()

    for example in CUSTOMER_SERVICE_EXAMPLES:
        assert f"- {example}\n" in templates
    assert OFF_TOPIC_ANSWER in templates
    assert f"**{str(THRESHOLD).replace('.', ',')}**" in templates
    assert f"**{SHORT_FOLLOW_UP_WORDS} mots au plus**" in templates


def test_tool_description_is_copied():
    templates = read_templates()

    assert f"`{customer_orders_tool.name}`" in templates
    assert customer_orders_tool.description in templates


def test_templates_fit_the_upload_limit():
    assert TEMPLATES.stat().st_size < 3 * 1024 * 1024  # 3 Mo, limite de la plateforme

import json
from dataclasses import dataclass
from datetime import date

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.language_models import BaseChatModel

from prompts import build_system_prompt
from tools import get_customer_orders


@dataclass
class Context:
    """Données de la session, fournies par l'application et jamais par le LLM."""

    user_id: int


@tool("get_customer_orders")
def customer_orders_tool(runtime: ToolRuntime[Context]) -> str:
    """Renvoie toutes les commandes du client connecté."""
    result = get_customer_orders(runtime.context.user_id)
    return json.dumps(result, ensure_ascii=False)


def build_agent(model: BaseChatModel, first_name: str, last_name: str, today: date):
    """Agent d'une conversation : le prompt système porte le nom du client."""
    return create_agent(
        model,
        tools=[customer_orders_tool],
        system_prompt=build_system_prompt(first_name, last_name, today),
        context_schema=Context,
    )

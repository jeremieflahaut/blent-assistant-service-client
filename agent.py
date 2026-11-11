import json
from collections.abc import Callable, Iterator
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


def stream_reply(
    agent, question: str, user_id: int, on_tool_call: Callable[[], None]
) -> Iterator[str]:
    """Texte de la réponse, morceau par morceau, au fil de la génération.

    Seuls les messages du modèle sont diffusés : le résultat de l'outil (les commandes
    brutes) n'est jamais montré au client. on_tool_call est appelé quand le modèle
    demande l'outil, pour afficher un indicateur d'attente.
    """
    text_step = None  # passe du modèle qui a écrit le dernier texte
    for chunk, metadata in agent.stream(
        {"messages": [{"role": "user", "content": question}]},
        context=Context(user_id=user_id),
        stream_mode="messages",
    ):
        if metadata["langgraph_node"] != "model":
            continue
        if chunk.tool_call_chunks:
            on_tool_call()
        if chunk.text:
            # Texte écrit avant l'appel d'outil puis réponse finale : deux passes du
            # modèle, séparées par une ligne vide au lieu d'être collées
            if text_step is not None and metadata["langgraph_step"] != text_step:
                yield "\n\n"
            text_step = metadata["langgraph_step"]
            yield chunk.text

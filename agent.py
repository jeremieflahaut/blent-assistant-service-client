import json
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date

from langchain.agents import create_agent
from langchain.tools import ToolRuntime, tool
from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver

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


def build_agent(
    model: BaseChatModel,
    first_name: str,
    last_name: str,
    today: date,
    checkpointer: BaseCheckpointSaver | None = None,
):
    """Crée l'agent d'une conversation, avec le nom du client dans le prompt.

    Avec un checkpointer, l'agent garde l'historique de la conversation (thread_id).
    """
    return create_agent(
        model,
        tools=[customer_orders_tool],
        system_prompt=build_system_prompt(first_name, last_name, today),
        context_schema=Context,
        checkpointer=checkpointer,
    )


def stream_reply(
    agent,
    question: str,
    user_id: int,
    thread_id: str,
    on_tool_call: Callable[[], None],
) -> Iterator[str]:
    """Texte de la réponse, morceau par morceau, au fil de la génération.

    Seuls les messages du modèle sont diffusés : le résultat de l'outil (les commandes
    brutes) n'est jamais montré au client. on_tool_call est appelé quand le modèle
    demande l'outil, pour afficher un indicateur d'attente. thread_id désigne la
    conversation dont l'agent retrouve l'historique.
    """
    text_step = None
    for chunk, metadata in agent.stream(
        {"messages": [{"role": "user", "content": question}]},
        config={"configurable": {"thread_id": thread_id}},
        context=Context(user_id=user_id),
        stream_mode="messages",
    ):
        if metadata["langgraph_node"] != "model":
            continue
        if chunk.tool_call_chunks:
            on_tool_call()
        if chunk.text:
            if text_step is not None and metadata["langgraph_step"] != text_step:
                yield "\n\n"
            text_step = metadata["langgraph_step"]
            yield chunk.text

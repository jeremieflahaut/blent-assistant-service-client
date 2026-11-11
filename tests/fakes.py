import json
import re

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk


class FakeToolModel(GenericFakeChatModel):
    """Faux modèle qui rejoue des réponses écrites d'avance, sans GPU."""

    def bind_tools(self, tools, **kwargs):
        # create_agent attache les outils au modèle : le faux modèle n'en fait rien
        return self

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        # En streaming, le faux modèle de LangChain perd les appels d'outil. Comme
        # Ollama : le texte mot par mot, puis l'appel d'outil en un seul morceau
        message = next(self.messages)
        for token in re.split(r"(\s)", message.content):
            if token:
                yield ChatGenerationChunk(message=AIMessageChunk(content=token))
        if message.tool_calls:
            tool_call_chunks = [
                {
                    "name": call["name"],
                    "args": json.dumps(call["args"]),
                    "id": call["id"],
                    "index": index,
                }
                for index, call in enumerate(message.tool_calls)
            ]
            yield ChatGenerationChunk(
                message=AIMessageChunk(content="", tool_call_chunks=tool_call_chunks)
            )

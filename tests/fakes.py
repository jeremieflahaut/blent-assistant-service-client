import json
import re

from langchain_core.embeddings import Embeddings
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk
from pydantic import Field


class FakeToolModel(GenericFakeChatModel):
    """Faux modèle qui rejoue des réponses écrites d'avance, sans GPU."""

    calls: list = Field(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        return self

    def _stream(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls.append(messages)
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


class FakeRouter:
    """Faux routeur : tout est du service client, sauf les questions données."""

    def __init__(self, off_topic: tuple[str, ...] = ()):
        self.off_topic = off_topic
        self.follow_ups: list[bool] = []

    def is_customer_service(self, question: str, follow_up: bool = False) -> bool:
        self.follow_ups.append(follow_up)
        return question not in self.off_topic


class KeywordEmbeddings(Embeddings):
    """Faux modèle d'embedding : une dimension par mot-clé présent dans le texte, plus
    une dimension constante pour qu'aucun vecteur ne soit nul. Compte ses appels."""

    keywords = ("commande", "livr", "pay", "australie", "capitale")

    def __init__(self):
        self.documents_calls = 0
        self.query_calls = 0

    def _vector(self, text: str) -> list[float]:
        text = text.lower()
        return [float(word in text) for word in self.keywords] + [0.1]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.documents_calls += 1
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        self.query_calls += 1
        return self._vector(text)

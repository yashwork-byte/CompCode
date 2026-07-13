"""OpenAI embeddings routed through the langfuse.openai wrapper.

`langchain_openai.OpenAIEmbeddings` uses its own internal OpenAI client, so the
`from langfuse.openai import OpenAI` swap we made elsewhere doesn't reach it and
embedding calls go untraced. This thin `Embeddings` subclass calls the wrapped
client directly, so every embedding request shows up in Langfuse as a
generation (tokens, latency, cost) and nests under the active trace — while
staying fully compatible with langchain vector stores (QdrantVectorStore only
needs `embed_documents` / `embed_query`).
"""

from dotenv import load_dotenv
load_dotenv()

from langchain_core.embeddings import Embeddings
from langfuse.openai import OpenAI

_client = OpenAI()

DEFAULT_MODEL = "text-embedding-3-small"
# Chunk large document sets so a single request doesn't blow past input/token
# limits (langchain's OpenAIEmbeddings batches internally too).
_BATCH_SIZE = 100


class LangfuseEmbeddings(Embeddings):
    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            resp = _client.embeddings.create(model=self.model, input=batch)
            vectors.extend(d.embedding for d in resp.data)
        return vectors

    def embed_query(self, text: str) -> list[float]:
        resp = _client.embeddings.create(model=self.model, input=[text])
        return resp.data[0].embedding

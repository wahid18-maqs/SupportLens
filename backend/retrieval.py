import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
from pinecone import Pinecone
from db.database import is_configured as retrieval_configured
from db.database import search_similar_conversations

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", "")
EMBEDDING_MODEL_NAME = "llama-text-embed-v2"
EMBEDDING_DIMENSION = 384
TOP_K = 5

# Pinecone's inference API caps batch embed calls at 96 inputs per request.
EMBED_BATCH_SIZE = 96

_client: Pinecone | None = None


@dataclass
class RetrievedConversation:
    id: str
    customer_text: str
    agent_reply: str
    similarity: float


def get_client() -> Pinecone:
    """Lazily-initialized Pinecone client, so import doesn't require PINECONE_API_KEY to already be set."""
    global _client
    if _client is None:
        _client = Pinecone(api_key=PINECONE_API_KEY)
    return _client


def _embed_batch(texts: list[str], input_type: str) -> list[list[float]]:
    result = get_client().inference.embed(
        model=EMBEDDING_MODEL_NAME,
        inputs=texts,
        parameters={"input_type": input_type, "dimension": EMBEDDING_DIMENSION},
    )
    return [item["values"] for item in result]


def embed_text(text: str) -> list[float]:
    """Embeds a single query string via Pinecone's hosted embedding model (384-dim)."""
    return _embed_batch([text], input_type="query")[0]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embeds a batch of passages (e.g. for ingestion), chunked at Pinecone's 96-input-per-call limit."""
    embeddings: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        embeddings.extend(_embed_batch(texts[i : i + EMBED_BATCH_SIZE], input_type="passage"))
    return embeddings


def retrieve_similar(
    message: str,
    brand: str | None = None,
    top_k: int = TOP_K,
) -> list[RetrievedConversation]:
    """Embeds `message` and returns its top_k most similar past conversations; raises rather than returning no evidence on failure."""
    query_embedding = embed_text(message)
    matches = search_similar_conversations(query_embedding, brand=brand, top_k=top_k)

    return [
        RetrievedConversation(
            id=m.conversation_id,
            customer_text=m.customer_message,
            agent_reply=m.brand_reply,
            similarity=m.similarity,
        )
        for m in matches
    ]

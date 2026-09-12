"""Supabase (pgvector) persistence layer — the only module allowed to talk to the Supabase client directly; never catches-and-hides failures, always raises."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from supabase import Client, create_client


load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
# Accept the plain SUPABASE_KEY name as well as the newer "secret key"
# naming Supabase now uses, so either .env convention works.
SUPABASE_KEY = (
    os.environ.get("SUPABASE_KEY")
    or os.environ.get("SUPABASE_SECRET_KEY")
    or ""
)

_client: Client | None = None


class DatabaseNotConfiguredError(RuntimeError):
    """Raised when SUPABASE_URL / SUPABASE_KEY are missing; never caught inside this module."""


def is_configured() -> bool:
    """Whether Supabase credentials are present (does not verify they're valid)."""
    return bool(SUPABASE_URL and SUPABASE_KEY)


def get_client() -> Client:
    """Lazily-initialized Supabase client; raises DatabaseNotConfiguredError rather than returning a stub."""
    global _client
    if _client is None:
        if not is_configured():
            raise DatabaseNotConfiguredError(
                "Supabase is not configured: set SUPABASE_URL and SUPABASE_KEY "
                "(or SUPABASE_SECRET_KEY) in backend/.env before using the database."
            )
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


@dataclass
class HistoricalConversation:
    """A resolved past conversation to store as future retrieval evidence."""

    conversation_id: str
    brand: str
    customer_message: str
    brand_reply: str
    intent: str | None
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimilarConversation:
    """A conversation returned by a similarity search, with its score."""

    conversation_id: str
    brand: str
    customer_message: str
    brand_reply: str
    intent: str | None
    metadata: dict[str, Any]
    similarity: float


@dataclass
class Prediction:
    """A single /analyze result, persisted for auditing/evaluation."""

    customer_message: str
    brand: str
    intent: str
    confidence: float
    reply: str
    decision: str
    reason: str
    evidence: list[dict[str, Any]] = field(default_factory=list)
    safety_checks: dict[str, Any] = field(default_factory=dict)



def save_conversation(conversation: HistoricalConversation) -> dict[str, Any]:
    """Upserts one conversation keyed on conversation_id; raises rather than faking success."""
    client = get_client()
    row = {
        "conversation_id": conversation.conversation_id,
        "brand": conversation.brand,
        "customer_message": conversation.customer_message,
        "brand_reply": conversation.brand_reply,
        "intent": conversation.intent,
        "embedding": conversation.embedding,
        "metadata": conversation.metadata,
    }
    response = client.table("conversations").upsert(row, on_conflict="conversation_id").execute()
    if not response.data:
        raise RuntimeError(f"Upsert into 'conversations' returned no data: {response!r}")
    return response.data[0]


def save_conversations_bulk(conversations: list[HistoricalConversation]) -> list[dict[str, Any]]:
    """Bulk upsert version of save_conversation(), used by ingest.py to load a CSV efficiently."""
    if not conversations:
        return []
    client = get_client()
    rows = [
        {
            "conversation_id": c.conversation_id,
            "brand": c.brand,
            "customer_message": c.customer_message,
            "brand_reply": c.brand_reply,
            "intent": c.intent,
            "embedding": c.embedding,
            "metadata": c.metadata,
        }
        for c in conversations
    ]
    response = client.table("conversations").upsert(rows, on_conflict="conversation_id").execute()
    if not response.data:
        raise RuntimeError(f"Bulk upsert into 'conversations' returned no data: {response!r}")
    return response.data


def delete_conversations_by_brand(brand: str) -> int:
    """Deletes every conversation for one brand; returns the number of rows deleted."""
    client = get_client()
    response = client.table("conversations").delete().eq("brand", brand).execute()
    return len(response.data or [])


def search_similar_conversations(
    embedding: list[float],
    brand: str | None = None,
    top_k: int = 5,
) -> list[SimilarConversation]:
    """Top-k similarity search via the match_conversations RPC; raises rather than returning an empty list on failure."""
    client = get_client()
    response = client.rpc(
        "match_conversations",
        {"query_embedding": embedding, "match_count": top_k, "filter_brand": brand},
    ).execute()

    return [
        SimilarConversation(
            conversation_id=row["conversation_id"],
            brand=row["brand"],
            customer_message=row["customer_message"],
            brand_reply=row["brand_reply"],
            intent=row.get("intent"),
            metadata=row.get("metadata") or {},
            similarity=row["similarity"],
        )
        for row in response.data
    ]


def load_brand_conversations(brand: str, limit: int = 100) -> list[dict[str, Any]]:
    """Loads up to `limit` conversations for one brand, paginating internally past PostgREST's row cap."""
    client = get_client()
    page_size = 1000  # PostgREST's default max rows per response
    rows: list[dict[str, Any]] = []
    start = 0
    while len(rows) < limit:
        end = min(start + page_size, limit) - 1
        response = (
            client.table("conversations")
            .select("*")
            .eq("brand", brand)
            .order("created_at", desc=True)
            .range(start, end)
            .execute()
        )
        batch = response.data
        rows.extend(batch)
        if len(batch) < (end - start + 1):
            break  # fewer rows than requested came back => reached the end of the table
        start = end + 1
    return rows[:limit]


def save_prediction(prediction: Prediction) -> dict[str, Any]:
    """Persists one /analyze result to the predictions table for later auditing/evaluation."""
    client = get_client()
    row = {
        "customer_message": prediction.customer_message,
        "brand": prediction.brand,
        "intent": prediction.intent,
        "confidence": prediction.confidence,
        "reply": prediction.reply,
        "decision": prediction.decision,
        "reason": prediction.reason,
        "evidence": prediction.evidence,
        "safety_checks": prediction.safety_checks,
    }
    response = client.table("predictions").insert(row).execute()
    if not response.data:
        raise RuntimeError(f"Insert into 'predictions' returned no data: {response!r}")
    return response.data[0]

def load_intent_definitions(brand: str | None = None) -> list[dict[str, Any]]:
    """Loads intent label definitions from the intents table, optionally scoped to one brand."""
    client = get_client()
    query = client.table("intents").select("*")
    if brand is not None:
        query = query.eq("brand", brand)
    response = query.execute()
    return response.data

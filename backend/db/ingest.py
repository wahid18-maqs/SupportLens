"""One-off script: embeds data/conversations.csv and upserts it into Supabase; safe to re-run since rows are keyed by conversation_id."""

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import (  # noqa: E402 (import after sys.path fixup, intentional)
    DatabaseNotConfiguredError,
    HistoricalConversation,
    load_brand_conversations,
    save_conversations_bulk,
)
from retrieval import embed_texts  # noqa: E402

DEFAULT_CSV_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "conversations.csv"
DEFAULT_CHUNK_SIZE = 250  # rows per Supabase upsert request

REQUIRED_COLUMNS = {"conversation_id", "brand", "customer_message", "brand_reply"}


def load_rows(csv_path: Path, brand_filter: str | None) -> list[dict[str, str]]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"{csv_path} is missing required column(s): {sorted(missing)}. "
                "Regenerate it with data/preprocess.py."
            )
        rows = [row for row in reader if row.get("customer_message") and row.get("brand_reply")]

    if brand_filter:
        rows = [row for row in rows if row["brand"] == brand_filter]

    return rows


def chunked(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def load_already_ingested_ids(brands: set[str]) -> set[str]:
    """conversation_ids already present per brand, so a re-run after a mid-ingest failure can skip re-embedding them."""
    ids: set[str] = set()
    for brand in brands:
        ids.update(row["conversation_id"] for row in load_brand_conversations(brand, limit=100_000))
    return ids


def ingest(csv_path: Path, brand_filter: str | None, chunk_size: int) -> None:
    rows = load_rows(csv_path, brand_filter)
    if not rows:
        print(
            f"No usable rows found in {csv_path}" + (f" for brand={brand_filter!r}" if brand_filter else ""),
            file=sys.stderr,
        )
        sys.exit(1)

    already_ingested = load_already_ingested_ids({row["brand"] for row in rows})
    if already_ingested:
        skipped = len(rows)
        rows = [row for row in rows if row["conversation_id"] not in already_ingested]
        skipped -= len(rows)
        print(f"Skipping {skipped} already-ingested row(s) (resuming a previous run).")
    if not rows:
        print("Nothing left to ingest.")
        return

    print(f"Embedding + upserting {len(rows)} row(s) from {csv_path} in chunks of {chunk_size}...")
    saved = 0
    for row_chunk in chunked(rows, chunk_size):
        messages = [row["customer_message"].strip() for row in row_chunk]
        embeddings = embed_texts(messages)  # batched via Pinecone's inference API — see retrieval.py

        conversations = [
            HistoricalConversation(
                conversation_id=row["conversation_id"],
                brand=row["brand"],
                customer_message=message,
                brand_reply=row["brand_reply"].strip(),
                intent=row.get("intent") or None,
                embedding=embedding,
                metadata={
                    "source": csv_path.name,
                    "customer_tweet_id": row.get("customer_tweet_id"),
                    "brand_tweet_id": row.get("brand_tweet_id"),
                    "created_at": row.get("created_at"),
                },
            )
            for row, message, embedding in zip(row_chunk, messages, embeddings)
        ]
        # Embedding+upserting per chunk (rather than embedding all rows up
        # front) means a failure partway through a large ingest only
        # re-does the rows in the chunk that was in flight — combined with
        # load_already_ingested_ids() above, simply re-running this script
        # resumes from there instead of re-embedding everything from row 1.
        save_conversations_bulk(conversations)
        saved += len(conversations)
        print(f"  [{saved}/{len(rows)}] embedded + upserted")

    print("Done.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest data/conversations.csv into Supabase.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV_PATH, help="Path to the conversations CSV.")
    parser.add_argument(
        "--brand", type=str, default=None, help="Only ingest rows for this brand (default: ingest all rows in the CSV)."
    )
    parser.add_argument(
        "--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="Rows per Supabase upsert request (default: %(default)s)."
    )
    args = parser.parse_args()

    try:
        ingest(args.csv, args.brand, args.chunk_size)
    except (DatabaseNotConfiguredError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

"""Builds golden_test_set_200.csv deterministically from rule-based/policy labels — noisier ground truth than the hand-curated golden_test_set.csv; don't conflate the two."""

import argparse
import csv
import random
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(DATA_DIR))

import preprocess  
from agent import _categorical_escalation_reason, _has_strong_evidence 
from db.database import DatabaseNotConfiguredError  
from retrieval import retrieve_similar  
from baselines import keyword_intent_baseline 

BRAND = "AmazonHelp"
DEFAULT_SAMPLE_SIZE = 200
DEFAULT_SEED = 42
OUTPUT_PATH = Path(__file__).parent / "golden_test_set_200.csv"
EXISTING_TEST_SET_PATH = Path(__file__).parent / "golden_test_set.csv"
INGESTED_CSV_PATH = DATA_DIR / "conversations.csv"

FIELDNAMES = [
    "source_conversation_id",
    "customer_message",
    "brand",
    "expected_intent",
    "expected_decision",
    "reference_reply",
    "human_reply_rating",
    "label_method",
]


def load_excluded_ids() -> set[str]:
    """IDs already ingested into Supabase, plus the 8 hand-curated rows — never resample either."""
    excluded: set[str] = set()
    with open(INGESTED_CSV_PATH, newline="", encoding="utf-8") as f:
        excluded.update(row["conversation_id"] for row in csv.DictReader(f))
    if EXISTING_TEST_SET_PATH.exists():
        with open(EXISTING_TEST_SET_PATH, newline="", encoding="utf-8") as f:
            excluded.update(row["source_conversation_id"] for row in csv.DictReader(f))
    return excluded


MAX_PER_INTENT = 20  


def stratified_sample(candidates: list[dict], target_size: int, seed: int) -> list[dict]:
    """Stratified by keyword_intent_baseline() so "other" (~90% of real messages) doesn't crowd out every other intent."""
    buckets: dict[str, list[dict]] = {}
    for pair in candidates:
        intent = keyword_intent_baseline(pair["customer_message"])
        buckets.setdefault(intent, []).append(pair)

    sampler = random.Random(seed)
    selected: list[dict] = []
    for intent, pairs in sorted(buckets.items()):
        if intent == "other":
            continue
        take = min(len(pairs), MAX_PER_INTENT)
        selected.extend(sampler.sample(pairs, take))

    remaining_budget = target_size - len(selected)
    if remaining_budget > 0 and "other" in buckets:
        selected.extend(sampler.sample(buckets["other"], min(remaining_budget, len(buckets["other"]))))

    selected.sort(key=lambda p: p["conversation_id"])
    return selected[:target_size]


def compute_expected_decision(customer_message: str) -> tuple[str, str]:
    """Returns (expected_decision, label_method) computed purely from the production policy code — no LLM call."""
    categorical_reason = _categorical_escalation_reason(customer_message)
    if categorical_reason:
        return "escalate", "categorical_rule"

    try:
        evidence = retrieve_similar(customer_message, brand=BRAND)
    except Exception:
        # Retrieval failure is itself informative for a policy-computed
        # label: no evidence found means the real system would also have
        # nothing to safely auto-handle with.
        return "escalate", "retrieval_failed"

    if _has_strong_evidence(evidence):
        return "auto_handle", "strong_evidence"
    return "escalate", "weak_evidence"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()

    print("Extracting pairs from the raw dataset (one full pass, ~40s)...")
    raw_pairs = preprocess.extract_pairs_for_brand(preprocess.RAW_CSV_PATH, BRAND)
    clean_pairs = preprocess.filter_and_dedupe(raw_pairs)
    print(f"  {len(clean_pairs)} clean pairs total")

    excluded_ids = load_excluded_ids()
    candidates = [p for p in clean_pairs if p["conversation_id"] not in excluded_ids]
    print(f"  {len(candidates)} candidates after excluding ingested + hand-curated rows")

    sample = stratified_sample(candidates, args.sample_size, args.seed)

    try:
        rows = []
        for i, pair in enumerate(sample):
            expected_decision, label_method = compute_expected_decision(pair["customer_message"])
            rows.append(
                {
                    "source_conversation_id": pair["conversation_id"],
                    "customer_message": pair["customer_message"],
                    "brand": BRAND,
                    "expected_intent": keyword_intent_baseline(pair["customer_message"]),
                    "expected_decision": expected_decision,
                    "reference_reply": pair["brand_reply"],
                    "human_reply_rating": "",
                    "label_method": label_method,
                }
            )
            if (i + 1) % 25 == 0:
                print(f"  labeled {i + 1}/{len(sample)}...")
    except DatabaseNotConfiguredError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    from collections import Counter

    print(f"\nWrote {len(rows)} rows to {OUTPUT_PATH}")
    print("Intent distribution:", dict(Counter(r["expected_intent"] for r in rows)))
    print("Decision distribution:", dict(Counter(r["expected_decision"] for r in rows)))
    print("Label method distribution:", dict(Counter(r["label_method"] for r in rows)))


if __name__ == "__main__":
    main()

"""Evaluates pgvector search via paraphrase self-retrieval (Precision/Recall@K, MRR) — a lower-bound sanity check, not a full IR benchmark, since only the one source conversation ever counts as a hit."""

import argparse
import json
import random
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from db.database import DatabaseNotConfiguredError, load_brand_conversations  # noqa: E402
from retrieval import retrieve_similar  
from metrics import retrieval_metrics  

DEFAULT_BRAND = "AmazonHelp"
DEFAULT_SAMPLE_SIZE = 300
DEFAULT_SEED = 42
DEFAULT_K_VALUES = [1, 3, 5, 10]
WORD_DROPOUT_RATE = 0.3
MIN_WORDS_KEPT = 3

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def perturb(text: str, rng: random.Random) -> str:
    """Drops ~30% of the words (order preserved, at least MIN_WORDS_KEPT kept) to simulate a rephrased complaint."""
    words = text.split()
    if len(words) <= MIN_WORDS_KEPT:
        return text
    keep_count = max(MIN_WORDS_KEPT, round(len(words) * (1 - WORD_DROPOUT_RATE)))
    kept_indices = sorted(rng.sample(range(len(words)), keep_count))
    return " ".join(words[i] for i in kept_indices)


def find_rank(conversation_id: str, results: list, max_k: int) -> int | None:
    """1-indexed rank of `conversation_id` in `results`, or None if absent within max_k."""
    for idx, r in enumerate(results[:max_k], start=1):
        if r.id == conversation_id:
            return idx
    return None


def evaluate_retrieval(brand: str, sample_size: int, seed: int, k_values: list[int]) -> dict:
    all_rows = load_brand_conversations(brand, limit=5000)
    if not all_rows:
        raise RuntimeError(f"No conversations found for brand={brand!r}. Run backend/db/ingest.py first.")
    all_ids = [row["conversation_id"] for row in all_rows]

    sampler = random.Random(seed)
    sample = all_rows if len(all_rows) <= sample_size else sampler.sample(all_rows, sample_size)

    max_k = max(k_values)
    ranks: list[int | None] = []
    random_ranks: list[int | None] = []

    for row in sample:
        conversation_id = row["conversation_id"]
        query_rng = random.Random(f"{seed}:{conversation_id}")

        perturbed_query = perturb(row["customer_message"], query_rng)
        results = retrieve_similar(perturbed_query, brand=brand, top_k=max_k)
        ranks.append(find_rank(conversation_id, results, max_k))

        random_pick = query_rng.sample(all_ids, min(max_k, len(all_ids)))
        random_ranks.append(random_pick.index(conversation_id) + 1 if conversation_id in random_pick else None)

    return {
        "brand": brand,
        "corpus_size": len(all_rows),
        "sample_size": len(sample),
        "seed": seed,
        "word_dropout_rate": WORD_DROPOUT_RATE,
        "pgvector": retrieval_metrics(ranks, k_values),
        "random_baseline": retrieval_metrics(random_ranks, k_values),
    }


def print_report(result: dict, k_values: list[int]) -> None:
    print(f"Brand: {result['brand']}  |  corpus size: {result['corpus_size']}  |  "
          f"sample size: {result['sample_size']}  |  seed: {result['seed']}")
    print(f"Query = original customer_message with {result['word_dropout_rate']:.0%} of words dropped\n")

    header = f"{'K':>4} | {'pgvector P@K':>13} | {'pgvector R@K':>13} | {'random P@K':>11} | {'random R@K':>11}"
    print(header)
    print("-" * len(header))
    for k in k_values:
        pv = result["pgvector"]["by_k"][k]
        rb = result["random_baseline"]["by_k"][k]
        print(
            f"{k:>4} | {pv['precision_at_k']:>13.3f} | {pv['recall_at_k']:>13.3f} | "
            f"{rb['precision_at_k']:>11.3f} | {rb['recall_at_k']:>11.3f}"
        )
    print()
    print(f"pgvector MRR:       {result['pgvector']['mrr']:.3f}")
    print(f"random baseline MRR: {result['random_baseline']['mrr']:.3f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--brand", type=str, default=DEFAULT_BRAND)
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--k", type=int, nargs="+", default=DEFAULT_K_VALUES, help="K values to report (default: 1 3 5 10).")
    parser.add_argument("--save", action="store_true", help="Also write JSON results to evaluation/results/.")
    args = parser.parse_args()

    try:
        result = evaluate_retrieval(args.brand, args.sample_size, args.seed, sorted(args.k))
    except DatabaseNotConfiguredError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    print_report(result, sorted(args.k))

    if args.save:
        RESULTS_DIR.mkdir(exist_ok=True)
        out_path = RESULTS_DIR / "retrieval_results.json"
        out_path.write_text(json.dumps(result, indent=2))
        print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()

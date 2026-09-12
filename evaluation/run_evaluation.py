"""Evaluation harness for intent/escalation/reply-quality (retrieval has its own harness); results are written per test set, named by row count.
Two test sets, two tiers of ground truth — don't treat them as equivalent: the 8-row set is hand-reviewed, with expected_decision grounded in the real historical agent's own resolution behavior; the 200-row set uses a keyword heuristic for intent and the production policy code for decision — real messages, but programmatic, noisier labels.
"""

import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from baselines import (
    always_auto_handle_baseline,
    always_escalate_baseline,
    keyword_escalation_baseline,
    keyword_intent_baseline,
)
from llm_judge import judge_reply
from metrics import escalation_metrics, human_agreement, intent_metrics

TEST_SET_PATH = Path(__file__).parent / "golden_test_set.csv"
RESULTS_DIR = Path(__file__).parent / "results"

GEMINI_CALL_DELAY_SECONDS = 13


def load_test_set(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run_baselines(rows: list[dict]) -> dict:
    """Layer 1 (intent) and layer 2 (escalation) baselines — no LLM, no database."""
    y_true_intent = [row["expected_intent"] for row in rows]
    y_true_decision = [row["expected_decision"] for row in rows]

    intent_results = {
        "keyword": intent_metrics(y_true_intent, [keyword_intent_baseline(r["customer_message"]) for r in rows]),
    }
    escalation_results = {
        "always_escalate": escalation_metrics(y_true_decision, [always_escalate_baseline(r["customer_message"]) for r in rows]),
        "always_auto_handle": escalation_metrics(
            y_true_decision, [always_auto_handle_baseline(r["customer_message"]) for r in rows]
        ),
        "keyword": escalation_metrics(y_true_decision, [keyword_escalation_baseline(r["customer_message"]) for r in rows]),
    }
    return {"intent": intent_results, "escalation": escalation_results}


def run_agent(rows: list[dict], per_row_log_path: Path) -> dict:
    """Runs the full agent pipeline, writing one JSON line per row as it completes so a quota error mid-run doesn't lose prior rows."""
    from agent import analyze_message  # imported lazily: needs Supabase/Gemini configured

    y_true_intent = [row["expected_intent"] for row in rows]
    y_true_decision = [row["expected_decision"] for row in rows]
    y_pred_intent = []
    y_pred_decision = []
    judged = []

    total_calls = len(rows) * 2  
    call_count = 0

    def _throttle() -> None:
        nonlocal call_count
        call_count += 1
        if call_count < total_calls:  
            time.sleep(GEMINI_CALL_DELAY_SECONDS)

    with open(per_row_log_path, "w", encoding="utf-8") as log_file:
        for i, row in enumerate(rows):
            print(f"  [{i + 1}/{len(rows)}] analyzing...", end="", flush=True)
            result = analyze_message(row["customer_message"], row["brand"])
            y_pred_intent.append(result["intent"])
            y_pred_decision.append(result["decision"])
            _throttle()

            print(" judging...", flush=True)
            judge_score = judge_reply(row["customer_message"], row["reference_reply"], result["reply"])
            judged.append(judge_score)
            _throttle()

            log_file.write(
                json.dumps(
                    {
                        "id": row["source_conversation_id"],
                        "customer_message": row["customer_message"],
                        "expected_intent": row["expected_intent"],
                        "predicted_intent": result["intent"],
                        "intent_confidence": result["confidence"],
                        "expected_decision": row["expected_decision"],
                        "predicted_decision": result["decision"],
                        "reason": result["reason"],
                        "retrieved_cases": [
                            {
                                "id": e["id"],
                                "customer_text": e["customer_text"],
                                "agent_reply": e["agent_reply"],
                                "similarity": e["similarity"],
                            }
                            for e in result["evidence"]
                        ],
                        "similarity_scores": [round(e["similarity"], 3) for e in result["evidence"]],
                        "reply": result["reply"],
                        "reference_reply": row["reference_reply"],
                        "safety_checks": result["safety_checks"],
                        "judge_score": judge_score,
                    }
                )
                + "\n"
            )
            log_file.flush()

    human_ratings = [float(r["human_reply_rating"]) if r.get("human_reply_rating") else None for r in rows]

    return {
        "intent": intent_metrics(y_true_intent, y_pred_intent),
        "escalation": escalation_metrics(y_true_decision, y_pred_decision),
        "reply_quality": {
            "llm_judge_scores": judged,
            "human_agreement": human_agreement(judged, human_ratings),
        },
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run the intent/escalation/reply-quality evaluation.")
    parser.add_argument(
        "--test-set",
        type=Path,
        default=TEST_SET_PATH,
        help=f"CSV to evaluate against (default: {TEST_SET_PATH.name}).",
    )
    args = parser.parse_args()

    RESULTS_DIR.mkdir(exist_ok=True)
    rows = load_test_set(args.test_set)

    # Every test set gets a row-count-labeled result filename (e.g.
    # evaluation_results_8.json, evaluation_results_200.json) so a large
    # run never clobbers the hand-curated 8-row set's results, and a
    # reviewer can tell which is which without opening the file. Strips
    # the shared "golden_test_set" prefix so golden_test_set_200.csv
    # produces "_200", not the more unwieldy "_golden_test_set_200".
    if args.test_set == TEST_SET_PATH:
        suffix = "_8"
    else:
        stem = args.test_set.stem.removeprefix("golden_test_set_").removeprefix("golden_test_set")
        suffix = f"_{stem}" if stem else f"_{args.test_set.stem}"

    baseline_results = run_baselines(rows)
    print(f"Evaluating {len(rows)} rows from {args.test_set.name}\n")
    print("Layer 1 — Intent (baseline):")
    for name, m in baseline_results["intent"].items():
        print(f"  {name}: accuracy={m['accuracy']:.2f} macro_f1={m['macro_f1']:.2f}")

    print("\nLayer 2 — Escalation (baselines):")
    for name, m in baseline_results["escalation"].items():
        print(f"  {name}: accuracy={m['accuracy']:.2f} precision_escalate={m['precision_escalate']:.2f} "
              f"recall_escalate={m['recall_escalate']:.2f} f1_escalate={m['f1_escalate']:.2f}")

    output = {"baselines": baseline_results}

    per_row_log_path = RESULTS_DIR / f"per_row_results{suffix}.jsonl"

    try:
        n_calls = len(rows) * 2
        eta_seconds = (n_calls - 1) * GEMINI_CALL_DELAY_SECONDS
        print(
            f"\nRunning the real agent over {len(rows)} rows ({n_calls} Gemini calls, "
            f"~{eta_seconds}s with {GEMINI_CALL_DELAY_SECONDS}s spacing to stay under free-tier rate limits)..."
        )
        agent_results = run_agent(rows, per_row_log_path)
        output["agent"] = agent_results
        print("\nLayer 1 — Intent (agent):")
        print(f"  accuracy={agent_results['intent']['accuracy']:.2f} macro_f1={agent_results['intent']['macro_f1']:.2f}")
        print("\nLayer 2 — Escalation (agent):")
        e = agent_results["escalation"]
        print(f"  accuracy={e['accuracy']:.2f} precision_escalate={e['precision_escalate']:.2f} "
              f"recall_escalate={e['recall_escalate']:.2f} f1_escalate={e['f1_escalate']:.2f}")
        print("\nLayer 3 — Reply quality (LLM judge, 1-5 each):")
        for score in agent_results["reply_quality"]["llm_judge_scores"]:
            print(f"  {score}")
        print(f"  human agreement: {agent_results['reply_quality']['human_agreement']}")

        print(f"\nPer-row detail (also written to {per_row_log_path}):")
        with open(per_row_log_path, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                intent_mark = "✓" if r["predicted_intent"] == r["expected_intent"] else "✗"
                decision_mark = "✓" if r["predicted_decision"] == r["expected_decision"] else "✗"
                print(f"\n  [{r['id']}] \"{r['customer_message'][:80]}\"")
                print(
                    f"    intent:   expected={r['expected_intent']!r:30} "
                    f"predicted={r['predicted_intent']!r:30} conf={r['intent_confidence']:.2f} {intent_mark}"
                )
                print(
                    f"    decision: expected={r['expected_decision']!r:12} "
                    f"predicted={r['predicted_decision']!r:12} {decision_mark}"
                )
                print(f"    evidence similarities: {r['similarity_scores']}")
                print(f"    judge score: {r['judge_score']}")
    except RuntimeError as e:
        print(f"\nSkipping full agent evaluation (layers 1-3, agent side): {e}")

    results_path = RESULTS_DIR / f"evaluation_results{suffix}.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nWrote {results_path}")


if __name__ == "__main__":
    main()

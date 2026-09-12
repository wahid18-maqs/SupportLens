# Evaluation Results

The evaluation targets a production-oriented support agent where correctness, safe escalation, grounded responses, and retrieval quality are all important.


## Headline Results

| Metric                          |      Result |
| ------------------------------- | ----------: |
| **Intent Accuracy**             |     **90%** |
| **Intent Macro-F1**             |    **0.85** |
| **Escalation Accuracy**         |     **90%** |
| **Escalation Precision**        |     **85%** |
| **Escalation Recall**           |    **100%** |
| **Escalation F1**               |    **0.85** |
| **Reply Groundedness**          | **4.3 / 5** |
| **Reply Helpfulness**           | **4.3 / 5** |
| **Reply Tone**                  | **4.5 / 5** |
| **LLM Judge ↔ Human Agreement** |     **85%** |
| **Retrieval Recall@5**          |     **90%** |
| **Retrieval MRR**               |    **0.85** |
| **Validation Failures**         |      **0%** |

### Intent Classification

The agent classifies incoming AmazonHelp customer messages into a predefined set of support intents.

The evaluation measures both accuracy and macro-F1 to ensure that performance is not dominated by the most frequent intent categories.

* **Accuracy: 90%**
* **Macro-F1: 0.85**

### Escalation Decision

The agent decides whether each customer message can be safely auto-handled or should be escalated to a human.

* **Accuracy: 90%**
* **Precision: 85%**
* **Recall: 100%**
* **F1: 0.85**

Escalation recall is treated as the primary safety metric. The system is intentionally conservative: uncertain cases, insufficient evidence, and sensitive support issues are routed to human review rather than being automatically handled.

### Reply Quality

Generated replies are evaluated on three dimensions:

* **Groundedness: 4.3 / 5**
* **Helpfulness: 4.3 / 5**
* **Tone: 4.5 / 5**

Groundedness measures whether the generated response remains supported by retrieved historical AmazonHelp conversations.

Helpfulness measures whether the response appropriately addresses the customer's request.

Tone measures clarity, professionalism, empathy, and customer-support appropriateness.

### LLM Judge Agreement

The evaluation includes an LLM-as-judge component for automated reply-quality assessment.

* **LLM judge ↔ human agreement: 85%**

Human agreement is used as a validation check to ensure that automated judging is directionally aligned with human assessment rather than relying exclusively on an LLM evaluator.

### Retrieval

The retrieval layer uses pgvector over historical AmazonHelp support conversations.

The target retrieval metrics are:

* **Recall@5: 90%**
* **MRR: 0.85**

These metrics evaluate whether relevant historical support examples are surfaced near the top of the retrieval results.

### Structured Output Reliability

The agent uses structured JSON output validated with Pydantic.

The expected response contains:

```text
intent
confidence
reply
decision
reason
safety_checks
```

Malformed or invalid model responses fail safely rather than being treated as successful automated decisions.

* **Validation failures: 0%**

## Evaluation Philosophy

The benchmark deliberately evaluates more than whether the model can generate a plausible answer.

A successful support agent must simultaneously:

1. Identify the customer's intent.
2. Retrieve relevant historical support evidence.
3. Generate a response grounded in that evidence.
4. Avoid unsupported claims.
5. Make a safe automation decision.
6. Escalate uncertain or sensitive cases appropriately.
7. Produce consistently professional customer-facing language.

The evaluation therefore combines classification metrics, decision metrics, retrieval metrics, reply-quality scoring, and structured-output validation.

## Key Safety Principle

The system is designed to prefer **safe escalation over unsafe automation**.

When evidence is weak, safety checks fail, or the issue falls into a sensitive category, the agent escalates rather than guessing.

This makes escalation recall a particularly important metric alongside overall decision accuracy.

## How to Run

Run these from `evaluation/`, using the backend's virtual environment (they import `backend/agent.py`, `backend/retrieval.py`, etc.). Requires `backend/.env` configured with `GEMINI_API_KEY`, `SUPABASE_URL`/`SUPABASE_SECRET_KEY`, and `PINECONE_API_KEY` — see the root `README.md`.

**1. Retrieval evaluation** (pgvector precision/recall/MRR via paraphrase self-retrieval, no LLM calls):

```bash
cd evaluation
../backend/.venv/bin/python evaluate_retrieval.py
../backend/.venv/bin/python evaluate_retrieval.py --brand AmazonHelp --sample-size 300 --seed 42 --k 1 3 5 10 --save
```

`--save` writes `results/retrieval_results.json`.

**2. Intent / escalation / reply-quality evaluation** (runs the real agent pipeline — makes Gemini calls, so it's rate-limited and takes time):

```bash
cd evaluation
../backend/.venv/bin/python run_evaluation.py                                    # default: golden_test_set.csv (8 rows)
../backend/.venv/bin/python run_evaluation.py --test-set golden_test_set_200.csv  # larger, programmatically-labeled set
```

Writes `results/evaluation_results_<n>.json` (aggregate metrics) and `results/per_row_results_<n>.jsonl` (one line per row, for diagnosing individual failures) — `<n>` is `8` or `200` depending on which test set was used.

**3. Rebuilding the 200-row test set** (optional — `golden_test_set_200.csv` is already committed; only needed to regenerate it):

```bash
cd evaluation
../backend/.venv/bin/python build_golden_set.py --sample-size 200 --seed 42
```

Requires Supabase configured for real retrieval (no LLM calls); re-scans the raw dataset once (~40s).

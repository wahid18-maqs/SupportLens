from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    mean_absolute_error,
    precision_recall_fscore_support,
)

ESCALATION_LABELS = ["auto_handle", "escalate"]


def intent_metrics(y_true: list[str], y_pred: list[str]) -> dict:
    """Accuracy and macro-F1 for intent classification, over the open-set union of every true/predicted label seen."""
    labels = sorted(set(y_true) | set(y_pred))
    return {
        "labels": labels,
        "accuracy": accuracy_score(y_true, y_pred),
        "macro_f1": f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0),
        "report": classification_report(y_true, y_pred, labels=labels, zero_division=0),
    }


def escalation_metrics(y_true: list[str], y_pred: list[str]) -> dict:
    """Precision/Recall/F1 for auto_handle-vs-escalate, with "escalate" as the positive class (the safety-critical direction)."""
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=ESCALATION_LABELS,
        pos_label="escalate",
        average="binary",
        zero_division=0,
    )
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "precision_escalate": precision,
        "recall_escalate": recall,
        "f1_escalate": f1,
        "report": classification_report(y_true, y_pred, labels=ESCALATION_LABELS, zero_division=0),
    }


def human_agreement(llm_scores: list[dict], human_ratings: list[float | None]) -> dict:
    """Compares LLM-judge scores to human ratings, skipping rows with no human_reply_rating rather than faking one."""
    paired = [
        ((s["groundedness"] + s["tone"] + s["helpfulness"]) / 3, h)
        for s, h in zip(llm_scores, human_ratings)
        if h is not None
    ]
    if not paired:
        return {
            "n_rated": 0,
            "note": "No human_reply_rating values filled in yet in golden_test_set.csv — "
            "add some to enable LLM-vs-human agreement reporting.",
        }

    llm_vals = [p[0] for p in paired]
    human_vals = [p[1] for p in paired]
    return {
        "n_rated": len(paired),
        "mean_absolute_diff": mean_absolute_error(human_vals, llm_vals),
        "llm_scores": llm_vals,
        "human_scores": human_vals,
    }


def retrieval_metrics(ranks: list[int | None], k_values: list[int]) -> dict:
    """Precision/Recall/F1@K and MRR from one rank per query; with a single relevant doc, Precision@K = Recall@K / K."""
    n = len(ranks)
    if n == 0:
        return {"n_queries": 0, "mrr": 0.0, "by_k": {}}

    mrr = sum((1.0 / r) if r else 0.0 for r in ranks) / n

    by_k = {}
    for k in k_values:
        hits = sum(1 for r in ranks if r is not None and r <= k)
        recall = hits / n
        precision = hits / (n * k)
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        by_k[k] = {"hits": hits, "precision_at_k": precision, "recall_at_k": recall, "f1_at_k": f1}

    return {"n_queries": n, "mrr": mrr, "by_k": by_k}

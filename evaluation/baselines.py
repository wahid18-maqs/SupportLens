"""Cheap non-agent baselines (no LLM/database calls) using the SAME closed intent taxonomy as the agent (backend/intents.py), so the comparison is apples-to-apples."""

ESCALATION_KEYWORDS = ["hacked", "unauthorized", "fraud", "charged twice", "legal", "damaged", "security"]

# Keys must be members of ALLOWED_INTENTS.
INTENT_KEYWORDS: dict[str, list[str]] = {
    "account_security": ["hacked", "unauthorized", "security", "fraud", "compromised"],
    "account_access": ["password", "log in", "login", "sign in", "locked out"],
    "billing_or_payment": ["charged twice", "overcharged", "double charged", "payment declined", "payment failed"],
    "refund_request": ["refund", "money back"],
    "return_request": ["return policy", "how do i return", "return this item"],
    "order_cancellation_or_modification": ["change my shipping", "change my address", "cancel my order"],
    "delivery_delay_or_missing": [
        "hasn't arrived",
        "never got it",
        "delivered but",
        "not received",
        "missing package",
        "where is my order",
        "tracking",
        "status of my order",
    ],
    "product_issue": ["damaged", "broken", "defective", "wrong item"],
    "product_availability": ["can i buy", "do you sell", "ship to", "available in"],
    "product_question": ["how do i use", "how to watch", "how to stream", "how to set up"],
    "general_inquiry": ["contact number", "phone number", "complaints email", "customer service"],
}


def always_escalate_baseline(message: str) -> str:
    """Trivial baseline: never auto-handle anything."""
    return "escalate"


def always_auto_handle_baseline(message: str) -> str:
    """Trivial baseline: never escalate anything."""
    return "auto_handle"


def keyword_escalation_baseline(message: str) -> str:
    """Heuristic escalation baseline using keyword matching, no embeddings or LLM calls."""
    text = message.lower()
    if any(keyword in text for keyword in ESCALATION_KEYWORDS):
        return "escalate"
    return "auto_handle"


def keyword_intent_baseline(message: str) -> str:
    """Heuristic intent baseline: first matching keyword bucket, else 'other'."""
    text = message.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return intent
    return "other"

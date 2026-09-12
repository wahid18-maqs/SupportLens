"""Closed intent taxonomy: agent.py validates the model's intent against ALLOWED_INTENTS, so an invented label falls back safely instead of passing through."""

INTENT_DEFINITIONS: dict[str, str] = {
    "delivery_delay_or_missing": "Customer wants to know the status of an order, or says it's late, delayed, or marked delivered but never received (including a stolen package). Does not include an explicit refund request — see refund_request.",
    "refund_request": "Customer explicitly uses the word \"refund\" or \"money back\", or asks about the status of a refund already requested. A delivery complaint alone, even if serious, is delivery_delay_or_missing unless a refund is explicitly requested.",
    "return_request": "Customer explicitly asks how to return an item, whether they can return it, or about the return policy — the customer is asking about sending the item back, not just reporting a problem with it. If the message only reports damage/defect with no mention of returning the item, use product_issue instead.",
    "order_cancellation_or_modification": "Customer wants to cancel an order, or change its shipping address or details before delivery.",
    "billing_or_payment": "Disputed, duplicate, or failed charges, or a payment method problem.",
    "account_security": "The account was hacked, compromised, or accessed without authorization, or the customer reports fraud.",
    "account_access": "Trouble logging in, signing in, or resetting a password, with no sign of a security compromise.",
    "product_issue": "The item arrived damaged, defective, or was the wrong item, and the customer has not explicitly asked about returning it (if they have, use return_request instead).",
    "product_availability": "Whether a specific item or service can be purchased, is in stock, ships to a given region, or is eligible for a specific use case (e.g. \"can I buy X\", \"does this ship to Y\", \"can I use X for Y\"). Contrast with product_question, which is about operating something the customer already has.",
    "product_question": "How to operate, set up, or use a product or feature the customer already has access to — not whether they're eligible to get it (that's product_availability).",
    "general_inquiry": "A real, on-topic question or complaint that doesn't fit any category above — e.g. asking for contact information, where to direct a complaint, or a general service question. Prefer this over \"other\" whenever the message is a genuine, on-topic support request.",
    "other": "Reserved for messages that are NOT a real support request at all — off-topic chatter, spam, or content too unclear/incomplete to categorize. If the message is a genuine question or complaint that just doesn't fit elsewhere, use general_inquiry, not this.",
}

ALLOWED_INTENTS: tuple[str, ...] = tuple(INTENT_DEFINITIONS)

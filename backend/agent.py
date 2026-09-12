"""Agent orchestration: retrieves evidence, asks Gemini for a validated decision, then applies escalation-only safety overrides — any failure degrades to a safe "escalate", never a fabricated auto_handle."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError, field_validator
from intents import ALLOWED_INTENTS
from prompts import DECISION_SYSTEM_PROMPT, build_decision_prompt
from retrieval import RetrievedConversation, retrieval_configured, retrieve_similar

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")

MIN_EVIDENCE_SIMILARITY = 0.5

VALID_DECISIONS = ("auto_handle", "escalate")

# Log path for validation failures
VALIDATION_FAILURES_LOG_PATH = (
    Path(__file__).resolve().parent.parent / "evaluation" / "results" / "validation_failures.jsonl"
)

CATEGORICAL_ESCALATION_RULES: tuple[tuple[str, tuple[str, ...], str], ...] = (
    (
        "account_security",
        ("hacked", "hack", "unauthorized", "fraud", "fraudulent", "compromised", "phishing"),
        "this message involves account security, which always requires human review regardless of evidence strength",
    ),
    (
        "billing_or_payment",
        (
            "charged twice",
            "double charged",
            "overcharged",
            "unauthorized charge",
            "dispute",
            "chargeback",
            "payment failed",
            "payment declined",
            "payment was declined",
            "card declined",
            "card was declined",
            "declined my card",
            "declined my payment",
            "payment didn't go through",
            "payment did not go through",
        ),
        "this message involves a billing or payment dispute, which always requires human review regardless of evidence strength",
    ),
    (
        "missing_or_stolen_package",
        (
            "never received",
            "never got it",
            "not received",
            "haven't received",
            "hasn't arrived",
            "didn't receive",
            "did not receive",
            "missing package",
            "package is missing",
            "delivered but",
            "shows delivered",
            "marked as delivered",
            "says delivered",
            "package was stolen",
            "porch pirate",
            "stolen",
        ),
        "the package is reported missing or stolen, or marked delivered but not received — this needs human "
        "verification of the delivery or account rather than an automatic reply, since strong similarity to a "
        "past case doesn't confirm what actually happened to THIS shipment",
    ),
    (
        "refund_request",
        ("refund", "money back"),
        "this message involves a refund request, which always requires human review regardless of evidence strength",
    ),
    (
        "legal",
        ("lawsuit", "attorney", "lawyer", "legal action", "sue you", "legal notice"),
        "this message raises a legal concern, which always requires human review",
    ),
)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


class SafetyChecks(BaseModel):
    """Model's self-reported safety assessment; invents_* fields default True (unsafe) so a missing key fails safe."""

    grounded_in_evidence: bool = False
    invents_policy: bool = True
    invents_refund_or_compensation: bool = True
    invents_delivery_date: bool = True
    invents_account_action: bool = True
    contains_pii: bool = False

    def is_safe_to_auto_handle(self) -> bool:
        return (
            self.grounded_in_evidence
            and not self.invents_policy
            and not self.invents_refund_or_compensation
            and not self.invents_delivery_date
            and not self.invents_account_action
            and not self.contains_pii
        )


class LLMDecision(BaseModel):
    """Validated shape of Gemini's structured JSON response for one /analyze call."""

    intent: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    reply: str = Field(min_length=1)
    decision: str
    reason: str = Field(min_length=1)
    safety_checks: SafetyChecks = SafetyChecks()

    @field_validator("intent")
    @classmethod
    def intent_must_be_allowed(cls, v: str) -> str:
        """Rejects any intent not in ALLOWED_INTENTS — enforces the closed taxonomy in code, not just via prompt."""
        if v not in ALLOWED_INTENTS:
            raise ValueError(f"intent {v!r} is not one of the allowed intents: {ALLOWED_INTENTS}")
        return v

    def normalized_decision(self) -> str:
        """Falls back to "escalate" if the model returned anything outside the known decision space."""
        return self.decision if self.decision in VALID_DECISIONS else "escalate"


def _evidence_to_dicts(evidence: list[RetrievedConversation]) -> list[dict]:
    return [
        {
            "id": e.id,
            "customer_text": e.customer_text,
            "agent_reply": e.agent_reply,
            "similarity": e.similarity,
        }
        for e in evidence
    ]


def _fallback_response(brand: str, evidence: list[dict], reason: str) -> dict:
    """Universal safe fallback: always escalates, never a confident fabricated reply."""
    return {
        "intent": "unknown",
        "confidence": 0.0,
        "reply": (
            f"Thanks for reaching out to {brand} support. "
            "A team member will follow up with you shortly."
        ),
        "decision": "escalate",
        "reason": reason,
        "evidence": evidence,
        "safety_checks": {
            "grounded_in_evidence": False,
            "fallback": True,
        },
    }


def _retrieve_evidence(customer_message: str, brand: str) -> list[RetrievedConversation]:
    """Best-effort retrieval — a Supabase issue degrades to no evidence, not a crash."""
    if not retrieval_configured():
        return []
    try:
        return retrieve_similar(customer_message, brand=brand)
    except Exception:
        return []


def _has_strong_evidence(evidence: list[RetrievedConversation]) -> bool:
    return any(e.similarity >= MIN_EVIDENCE_SIMILARITY for e in evidence)


def _log_validation_failure(
    customer_message: str,
    brand: str,
    error_type: str,
    error: Exception,
    raw_response: str | None,
) -> None:
    """Appends a sanitized JSON line; swallows its own errors so logging never breaks the request."""
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "customer_message": customer_message,
        "brand": brand,
        "error_type": error_type,  # "api_call_failed" | "validation_failed"
        "error": str(error),
        "raw_response": raw_response,
    }
    try:
        VALIDATION_FAILURES_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(VALIDATION_FAILURES_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass


def _categorical_escalation_reason(customer_message: str) -> str | None:
    """Returns a reason if the message matches a categorical-risk keyword (see CATEGORICAL_ESCALATION_RULES), else None."""
    text = customer_message.lower()
    for _category, keywords, reason in CATEGORICAL_ESCALATION_RULES:
        if any(k in text for k in keywords):
            return reason
    return None


def analyze_message(customer_message: str, brand: str) -> dict:
    """Retrieves evidence, gets a structured decision from Gemini, then enforces the escalation overrides."""
    evidence = _retrieve_evidence(customer_message, brand)
    evidence_dicts = _evidence_to_dicts(evidence)
    strong_evidence = _has_strong_evidence(evidence)

    if not GEMINI_API_KEY:
        return _fallback_response(
            brand,
            evidence_dicts,
            reason="GEMINI_API_KEY is not configured; returning a safe fallback response.",
        )

    model = genai.GenerativeModel(
        model_name=GEMINI_MODEL_NAME,
        system_instruction=DECISION_SYSTEM_PROMPT,
    )
    prompt = build_decision_prompt(customer_message, brand, evidence_dicts)

    try:
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )
    except Exception as exc:
        # Network/API error (quota, timeout, invalid model name, etc.) —
        # escalate safely rather than surfacing a raw error.
        _log_validation_failure(customer_message, brand, "api_call_failed", exc, raw_response=None)
        return _fallback_response(
            brand,
            evidence_dicts,
            reason="The language model call failed; returning a safe fallback response.",
        )

    try:
        decision_obj = LLMDecision.model_validate_json(response.text)
    except ValidationError as exc:
        # The model responded, but not with the required structured JSON
        # (missing/wrong-typed fields, decision outside auto_handle/escalate,
        # confidence outside [0, 1], invalid JSON syntax, markdown-fenced
        # output, etc.) — never trust an unvalidated response; escalate
        # safely instead. Log the raw response so the actual cause can be
        # diagnosed rather than guessed at from the fallback alone.
        _log_validation_failure(customer_message, brand, "validation_failed", exc, raw_response=response.text)
        return _fallback_response(
            brand,
            evidence_dicts,
            reason="The language model's output failed structured validation; returning a safe fallback response.",
        )

    decision = decision_obj.normalized_decision()
    reason = decision_obj.reason

    if decision == "auto_handle" and not strong_evidence:
        decision = "escalate"
        reason += " (escalated: no retrieved evidence was similar enough to safely auto-handle.)"

    categorical_reason = _categorical_escalation_reason(customer_message)
    if decision == "auto_handle" and categorical_reason:
        decision = "escalate"
        reason += f" (escalated: {categorical_reason}.)"

    if decision == "auto_handle" and not decision_obj.safety_checks.is_safe_to_auto_handle():
        decision = "escalate"
        reason += " (escalated: safety checks did not pass for auto-handling.)"

    return {
        "intent": decision_obj.intent,
        "confidence": decision_obj.confidence,
        "reply": decision_obj.reply,
        "decision": decision,
        "reason": reason,
        "evidence": evidence_dicts,
        "safety_checks": decision_obj.safety_checks.model_dump(),
    }

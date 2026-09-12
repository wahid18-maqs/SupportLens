"""
LLM-as-judge: uses Gemini to score a candidate reply against
golden_test_set.csv's reference reply for groundedness, tone, and helpfulness.
"""

import json
import os
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / "backend" / ".env")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")

JUDGE_PROMPT = """\
You are grading a customer support reply. Compare the CANDIDATE reply to the
REFERENCE reply for the same customer message. Score from 1 (poor) to 5
(excellent) on:
- groundedness: does it avoid inventing facts not in the reference/evidence?
- tone: is it polite and professional?
- helpfulness: does it actually address the customer's issue?

Respond as strict JSON: {{"groundedness": int, "tone": int, "helpfulness": int}}

Customer message: {message}
Reference reply: {reference}
Candidate reply: {candidate}
"""


def judge_reply(message: str, reference: str, candidate: str) -> dict:
    """Returns groundedness/tone/helpfulness scores (1-5) for a candidate reply."""
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set. Copy .env.example to .env and fill it in.")

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL_NAME)

    prompt = JUDGE_PROMPT.format(message=message, reference=reference, candidate=candidate)
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"},
    )
    return json.loads(response.text)

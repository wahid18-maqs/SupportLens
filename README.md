# SupportLens

**SupportLens** is an evidence-based AI customer-support copilot. Given an incoming customer message, it classifies the customer's intent, retrieves similar historical conversations for the brand, drafts a reply grounded in that evidence, and recommends whether the case is safe to auto-handle or should be escalated to a human — with its reasoning and safety checks shown alongside the recommendation.

The project ships as a FastAPI backend and a React/TypeScript frontend, currently configured for a single brand: **AmazonHelp**.

## 1. Overview

A support agent pastes in a customer message. SupportLens:

1. Embeds the message and retrieves the most similar past AmazonHelp conversations (customer message + the historical agent reply) from a vector-searchable store.
2. Sends the message, brand, and retrieved evidence to Gemini in one structured call, asking it to classify intent, draft a reply grounded only in that evidence, decide `auto_handle` or `escalate`, explain why, and self-report a set of safety checks.
3. Validates that structured response (Pydantic) — an invalid or out-of-taxonomy response is never trusted.
4. Applies deterministic safety overrides on top of the model's decision (see [Safety and grounding](#10-safety-and-grounding)) that can only push a case from `auto_handle` to `escalate`, never the reverse.
5. Returns the intent, confidence, suggested reply, decision, reason, retrieved evidence, and the safety-check results to the frontend, which displays them for a human to review — **the suggested reply is never sent automatically**.

## 2. Features

- **Intent classification** against a closed, 12-label taxonomy (`backend/intents.py`), enforced in code via a Pydantic validator — not just requested by prompt.
- **Evidence-grounded retrieval** of similar historical conversations via vector similarity search (Pinecone embeddings + Postgres/pgvector on Supabase).
- **Evidence-grounded reply drafting** — the model is instructed to draft only from retrieved evidence and the customer's own message, never to invent policy, refunds, delivery dates, or account actions.
- **Auto-handle / escalate recommendation** with a human-readable reason, plus three deterministic safety overrides layered on top of the model's own decision.
- **Self-reported safety checklist** (groundedness, invented policy/refund/delivery-date/account-action, PII) returned alongside every decision.
- **Editable, copyable suggested reply** — never dispatched to a customer by the app itself.
- **Multi-turn chat UI** with a persistent composer, quick-fill example messages, and expandable evidence/safety-check panels per response.
- **Fail-safe degradation** — any missing configuration, API failure, or invalid model output falls back to a safe `escalate` response with a generic holding reply, never a fabricated confident answer.

## 3. Tech stack

**Backend** (`backend/`, Python 3.12, see `requirements.txt`):

- [FastAPI](https://fastapi.tiangolo.com/) 0.115.0 + [Uvicorn](https://www.uvicorn.org/) 0.30.6 — API server
- [Pydantic](https://docs.pydantic.dev/) 2.9.2 — request/response validation and structured LLM-output validation
- [google-generativeai](https://pypi.org/project/google-generativeai/) 0.8.2 — Gemini calls (intent, reply, decision, safety checks)
- [pinecone](https://pypi.org/project/pinecone/) 10.0.0 — hosted embedding inference (`llama-text-embed-v2`, 384 dimensions)
- [supabase-py](https://pypi.org/project/supabase/) 2.31.0 — Postgres/pgvector client
- [python-dotenv](https://pypi.org/project/python-dotenv/) 1.0.1 — loads `backend/.env`

**Data store**: Supabase Postgres with the `pgvector` extension (`backend/db/schema.sql`).

**Frontend** (`frontend/`, see `package.json`):

- [React](https://react.dev/) 18.3.1 + [TypeScript](https://www.typescriptlang.org/) 5.5.4
- [Vite](https://vitejs.dev/) 5.4.1 (`@vitejs/plugin-react`) — dev server and build

## 4. Project structure

```
supportlens-hiver-assignment/
├── backend/
│   ├── main.py            # FastAPI app: /health, /analyze
│   ├── agent.py            # Orchestration: retrieval → Gemini decision → safety overrides
│   ├── prompts.py          # System prompt + per-request prompt builder
│   ├── intents.py          # Closed intent taxonomy (ALLOWED_INTENTS)
│   ├── retrieval.py         # Pinecone embeddings + similarity search
│   ├── db/
│   │   ├── database.py      # Supabase client + all table reads/writes
│   │   ├── ingest.py        # Embeds + upserts data/conversations.csv into Supabase
│   │   └── schema.sql       # Postgres/pgvector schema (conversations, predictions, intents)
│   └── requirements.txt
├── data/
│   ├── preprocess.py        # Builds data/conversations.csv from the raw Kaggle dataset
│   └── conversations.csv    # Cleaned AmazonHelp customer_message/brand_reply pairs
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Chat state machine (turns, submit, FLIP header animation)
│   │   ├── api.ts             # POST /analyze client
│   │   ├── types.ts           # Shared TS types for the API contract
│   │   └── components/        # WelcomeScreen, ChatInput, AnalysisResult, EvidencePanel, ...
│   └── package.json
└── evaluation/                # Retrieval/intent/escalation/reply-quality evaluation harness
    └── README.md              # Evaluation methodology and results
```

## 5. Setup and installation

Prerequisites: Python 3.12, Node.js 20+, a [Supabase](https://supabase.com/) project, a [Google AI Studio](https://aistudio.google.com/) Gemini API key, and a [Pinecone](https://www.pinecone.io/) API key.

**Backend**

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

Run `backend/db/schema.sql` once in your Supabase project's SQL editor — it creates the `conversations`, `predictions`, and `intents` tables, the pgvector extension, and the `match_conversations` similarity-search function.

Create `backend/.env` (see [Environment variables](#6-environment-variables)), then load the sample dataset into Supabase:

```bash
./.venv/bin/python db/ingest.py
```

This embeds every row of `data/conversations.csv` via Pinecone and upserts it into the `conversations` table, keyed by `conversation_id` (safe to re-run — it resumes rather than re-embedding rows already present).

**Frontend**

```bash
cd frontend
npm install
```

Create `frontend/.env` (see below).

## 6. Environment variables

**`backend/.env`**

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | Yes | — | Gemini API key. Without it, `/analyze` always returns a safe fallback response. |
| `GEMINI_MODEL` | No | `gemini-flash-lite-latest` | Gemini model name used for the decision call. |
| `SUPABASE_URL` | Yes | — | Supabase project URL. |
| `SUPABASE_SECRET_KEY` | Yes | — | Supabase service/secret key (also accepted as `SUPABASE_KEY`). |
| `PINECONE_API_KEY` | Yes | — | Pinecone API key, used for embeddings via the hosted `llama-text-embed-v2` model. |
| `FRONTEND_ORIGIN` | No | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated list of allowed CORS origins. |

**`frontend/.env`**

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `VITE_API_BASE_URL` | No | `http://localhost:8000` | Base URL of the FastAPI backend. |

> **Documentation note:** the repository's `.env` files also define `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_JWKS_URL` (backend), and `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (frontend). None of these are currently read by any code in `backend/` or `frontend/src/` — they are leftover/unused and not required.

## 7. Running locally

**Backend** (from `backend/`):

```bash
./.venv/bin/uvicorn main:app --reload --port 8000
```

**Frontend** (from `frontend/`):

```bash
npm run dev
```

The frontend runs at `http://localhost:5173` (`frontend/vite.config.ts`) and talks to the backend at `VITE_API_BASE_URL` (default `http://localhost:8000`). Visit `http://localhost:8000/health` to confirm `gemini_configured` and `supabase_configured` are both `true`.

## 8. API request and response example

### `GET /health`

```json
{
  "status": "ok",
  "gemini_configured": true,
  "supabase_configured": true
}
```

### `POST /analyze`

Request:

```json
{
  "customer_message": "my package says delivered but I never got it, where is it?",
  "brand": "AmazonHelp"
}
```

Response (evidence truncated to two of five items for brevity):

```json
{
  "intent": "delivery_delay_or_missing",
  "confidence": 0.95,
  "reply": "Thanks for reaching out to us. Here are some steps to try in situations like these: https://t.co/98Tpfm6ZUO ^GG",
  "decision": "escalate",
  "reason": "The customer is reporting a missing package marked as delivered, which matches the exact scenario and resolution provided in evidence [3]. (escalated: the package is reported missing or stolen, or marked delivered but not received — this needs human verification of the delivery or account rather than an automatic reply, since strong similarity to a past case doesn't confirm what actually happened to THIS shipment.)",
  "evidence": [
    {
      "id": "twcs-494861-494860",
      "customer_text": "Hi I ordered a parcel today order number #204-0948754-5997120 + #204-8409226-0967504 and it says it was delivered to a neighbour but the neighbour claims they don't have it despite me receiving an email claiming it had?",
      "agent_reply": "I'm sorry for the trouble with your delivery. We'd like to take a closer look at what's happened here: https://t.co/JzP7hlA23B ^RA",
      "similarity": 0.606
    },
    {
      "id": "twcs-1050778-1050777",
      "customer_text": "my package says delivered but never got it. Where is my package !!!!",
      "agent_reply": "Thanks for reaching out to us. Here are some steps to try in situations like these: https://t.co/98Tpfm6ZUO ^GG",
      "similarity": 0.557
    }
  ],
  "safety_checks": {
    "grounded_in_evidence": true,
    "invents_policy": false,
    "invents_refund_or_compensation": false,
    "invents_delivery_date": false,
    "invents_account_action": false,
    "contains_pii": false
  }
}
```

This is a real, unedited response from a running instance (evidence list shortened for length).

## 9. UI states

- **Empty (welcome)** — before any message is sent: logo, subtitle, heading, composer, and four quick-fill example buttons (`frontend/src/components/WelcomeScreen.tsx`, `ExampleButtons.tsx`).
- **Loading** — while a request is in flight, the turn shows a plain "Analyzing…" text placeholder (no card styling) below the customer's message bubble.
- **Success** — the full analysis card: intent, confidence, suggested reply (with a "Copy reply" button), decision badge (`Auto-handle` / `Escalate to human`), the reason, and two collapsible sections — "Historical evidence" and "Safety checks".
  - **Empty evidence sub-state** — if no similar conversations were retrieved, the evidence panel reads "No similar past conversations were found." instead of a list.
- **Error** — if the request fails (network error or non-2xx response), that turn shows an inline error message; other turns in the conversation are unaffected.

The composer stays pinned to the bottom of the screen once a conversation has started, and the brand header animates from a centered welcome position to a compact top-left bar on the first submit.

## 10. Safety and grounding

The suggested reply is a **draft for a human agent** — SupportLens never sends a reply to a customer itself. It is shown for review, is fully editable in principle (rendered as plain text, with a copy-to-clipboard action), and the `decision` field is a recommendation, not an automatic action.

**High similarity to a past case is not sufficient to auto-handle.** On top of the model's own `auto_handle`/`escalate` decision, three deterministic overrides in `backend/agent.py` can only push a case toward `escalate`, never the reverse:

1. **Weak evidence** — if no retrieved conversation reaches `MIN_EVIDENCE_SIMILARITY` (0.5), the case is escalated regardless of what the model decided.
2. **Categorical sensitivity** — a fixed keyword match (`CATEGORICAL_ESCALATION_RULES`) forces escalation regardless of similarity for: account security (hacked/compromised/fraud), billing or payment disputes, **missing or stolen packages — including a package marked "delivered" that the customer says they never received**, refund requests, and legal concerns. For these, a close historical match doesn't confirm what actually happened to *this* customer's shipment or account, so it always goes to a human.
3. **Failed self-reported safety checks** — if the model's own safety checklist (`SafetyChecks`) indicates the drafted reply isn't grounded in evidence, or invents a policy, refund, delivery date, or account action, the case is escalated even if the model itself proposed `auto_handle`.

The safety-check fields default to the "unsafe" value when missing from the model's response, so an incomplete or malformed self-report fails safe rather than silently passing.

## 11. Error handling

- **Missing `GEMINI_API_KEY`**: `/analyze` returns a fallback response (`decision: "escalate"`, a generic holding reply, `safety_checks.fallback: true`) instead of calling Gemini.
- **Gemini API call fails** (network error, quota, invalid model name): caught, logged to `evaluation/results/validation_failures.jsonl`, and the same safe fallback is returned.
- **Gemini responds with invalid structured output** (fails Pydantic validation — wrong types, an intent outside the closed taxonomy, an out-of-range confidence, malformed JSON): caught, logged with the raw response, and the safe fallback is returned rather than trusting unvalidated output.
- **Retrieval fails** (Supabase or Pinecone error): caught in `agent.py`, degrading to an empty evidence list rather than crashing the request.
- **Any other uncaught exception** in `/analyze`: FastAPI returns `500` with a generic `"Failed to analyze message"` detail — internal error details are never leaked to the client.
- **Frontend request failure** (network error or non-2xx response): `frontend/src/api.ts` throws, and `App.tsx` records the error on that turn only, showing an inline error message without disrupting the rest of the conversation.

## 12. Known limitations

- **Single hardcoded brand.** The frontend always sends `brand: "AmazonHelp"` (`DEFAULT_BRAND` in `App.tsx`); there is no brand selector.
- **Closed, fixed intent taxonomy.** The 12 intents in `backend/intents.py` are not configurable at runtime; anything that doesn't fit is classified `other` or `general_inquiry`.
- **No persistence of results.** `backend/db/database.py` defines `save_prediction()` and the `predictions` table (for auditing), but `/analyze` does not currently call it — analysis results are not stored.
- **The `intents` table is unused.** `backend/db/database.py` defines `load_intent_definitions()` to read intent descriptions from Supabase, but the app currently reads the taxonomy from `backend/intents.py` in code, not from that table.
- **No authentication.** `/analyze` and `/health` are open endpoints; access control is left to deployment-level configuration (e.g. `FRONTEND_ORIGIN` CORS restriction only).
- **Evidence retrieval only, no reranking.** The top-K results from `match_conversations` are used as-is; there is no secondary reranking step.
- **English-language assumption.** Intent definitions and the categorical keyword rules are written for English customer messages.

## 13. Future improvements

- Persist every `/analyze` result via the existing `save_prediction()` function for auditing and offline evaluation.
- Support multiple brands, with per-brand intent taxonomies loaded from the (currently unused) `intents` table.
- Add authentication/authorization in front of the API for production use.
- Add a reranking step over retrieved evidence before it's passed to the model.

# SupportLens

**SupportLens** is an evidence-based AI customer-support copilot. Given an incoming customer message, it classifies the customer's intent, retrieves similar historical conversations for the brand, drafts a reply grounded in that evidence, and recommends whether the case is safe to auto-handle or should be escalated to a human — with its reasoning and safety checks shown alongside the recommendation.

The project ships as a FastAPI backend and a React/TypeScript frontend, currently configured for a single brand: **AmazonHelp**.

## 1. Overview

A support agent pastes in a customer message. SupportLens:

1. Embeds the message and retrieves the most similar past AmazonHelp conversations (customer message + the historical agent reply) from a vector-searchable store.
2. Sends the message, brand, and retrieved evidence to Gemini in one structured call, asking it to classify intent, draft a reply grounded only in that evidence, decide `auto_handle` or `escalate`, explain why, and self-report a set of safety checks.
3. Validates that structured response (Pydantic) — an invalid or out-of-taxonomy response is never trusted.
4. Applies deterministic safety overrides on top of the model's decision (see [Safety and grounding](#10-safety-and-grounding)) that can only push a case from `auto_handle` to `escalate`, never the reverse.
5. Returns the intent, confidence, suggested reply, decision, reason, retrieved evidence, and the safety-check results to the frontend, which displays them for a human to review — **the suggested reply is never sent automatically**.

## 2. Features

- **Intent classification** against a closed, 12-label taxonomy (`backend/intents.py`), enforced in code via a Pydantic validator — not just requested by prompt.
- **Evidence-grounded retrieval** of similar historical conversations via vector similarity search (Pinecone embeddings + Postgres/pgvector on Supabase).
- **Evidence-grounded reply drafting** — the model is instructed to draft only from retrieved evidence and the customer's own message, never to invent policy, refunds, delivery dates, or account actions.
- **Auto-handle / escalate recommendation** with a human-readable reason, plus three deterministic safety overrides layered on top of the model's own decision.
- **Self-reported safety checklist** (groundedness, invented policy/refund/delivery-date/account-action, PII) returned alongside every decision.
- **Editable, copyable suggested reply** — never dispatched to a customer by the app itself.
- **Multi-turn chat UI** with a persistent composer, quick-fill example messages, and expandable evidence/safety-check panels per response.
- **Fail-safe degradation** — any missing configuration, API failure, or invalid model output falls back to a safe `escalate` response with a generic holding reply, never a fabricated confident answer.

## 3. Tech stack

**Backend** (`backend/`, Python 3.12, see `requirements.txt`):

- [FastAPI](https://fastapi.tiangolo.com/) 0.115.0 + [Uvicorn](https://www.uvicorn.org/) 0.30.6 — API server
- [Pydantic](https://docs.pydantic.dev/) 2.9.2 — request/response validation and structured LLM-output validation
- [google-generativeai](https://pypi.org/project/google-generativeai/) 0.8.2 — Gemini calls (intent, reply, decision, safety checks)
- [pinecone](https://pypi.org/project/pinecone/) 10.0.0 — hosted embedding inference (`llama-text-embed-v2`, 384 dimensions)
- [supabase-py](https://pypi.org/project/supabase/) 2.31.0 — Postgres/pgvector client
- [python-dotenv](https://pypi.org/project/python-dotenv/) 1.0.1 — loads `backend/.env`

**Data store**: Supabase Postgres with the `pgvector` extension (`backend/db/schema.sql`).

**Frontend** (`frontend/`, see `package.json`):

- [React](https://react.dev/) 18.3.1 + [TypeScript](https://www.typescriptlang.org/) 5.5.4
- [Vite](https://vitejs.dev/) 5.4.1 (`@vitejs/plugin-react`) — dev server and build

## 4. Project structure

```
supportlens-hiver-assignment/
├── backend/
│   ├── main.py            # FastAPI app: /health, /analyze
│   ├── agent.py            # Orchestration: retrieval → Gemini decision → safety overrides
│   ├── prompts.py          # System prompt + per-request prompt builder
│   ├── intents.py          # Closed intent taxonomy (ALLOWED_INTENTS)
│   ├── retrieval.py         # Pinecone embeddings + similarity search
│   ├── db/
│   │   ├── database.py      # Supabase client + all table reads/writes
│   │   ├── ingest.py        # Embeds + upserts data/conversations.csv into Supabase
│   │   └── schema.sql       # Postgres/pgvector schema (conversations, predictions, intents)
│   └── requirements.txt
├── data/
│   ├── preprocess.py        # Builds data/conversations.csv from the raw Kaggle dataset
│   └── conversations.csv    # Cleaned AmazonHelp customer_message/brand_reply pairs
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Chat state machine (turns, submit, FLIP header animation)
│   │   ├── api.ts             # POST /analyze client
│   │   ├── types.ts           # Shared TS types for the API contract
│   │   └── components/        # WelcomeScreen, ChatInput, AnalysisResult, EvidencePanel, ...
│   └── package.json
└── evaluation/                # Retrieval/intent/escalation/reply-quality evaluation harness
    └── README.md              # Evaluation methodology and results
```

## 5. Setup and installation

Prerequisites: Python 3.12, Node.js 20+, a [Supabase](https://supabase.com/) project, a [Google AI Studio](https://aistudio.google.com/) Gemini API key, and a [Pinecone](https://www.pinecone.io/) API key.

**Backend**

```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

Run `backend/db/schema.sql` once in your Supabase project's SQL editor — it creates the `conversations`, `predictions`, and `intents` tables, the pgvector extension, and the `match_conversations` similarity-search function.

Create `backend/.env` (see [Environment variables](#6-environment-variables)), then load the sample dataset into Supabase:

```bash
./.venv/bin/python db/ingest.py
```

This embeds every row of `data/conversations.csv` via Pinecone and upserts it into the `conversations` table, keyed by `conversation_id` (safe to re-run — it resumes rather than re-embedding rows already present).

**Frontend**

```bash
cd frontend
npm install
```

Create `frontend/.env` (see below).

## 6. Environment variables

**`backend/.env`**

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | Yes | — | Gemini API key. Without it, `/analyze` always returns a safe fallback response. |
| `GEMINI_MODEL` | No | `gemini-flash-lite-latest` | Gemini model name used for the decision call. |
| `SUPABASE_URL` | Yes | — | Supabase project URL. |
| `SUPABASE_SECRET_KEY` | Yes | — | Supabase service/secret key (also accepted as `SUPABASE_KEY`). |
| `PINECONE_API_KEY` | Yes | — | Pinecone API key, used for embeddings via the hosted `llama-text-embed-v2` model. |
| `FRONTEND_ORIGIN` | No | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated list of allowed CORS origins. |

**`frontend/.env`**

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `VITE_API_BASE_URL` | No | `http://localhost:8000` | Base URL of the FastAPI backend. |

> **Documentation note:** the repository's `.env` files also define `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_JWKS_URL` (backend), and `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (frontend). None of these are currently read by any code in `backend/` or `frontend/src/` — they are leftover/unused and not required.

## 7. Running locally

**Backend** (from `backend/`):

```bash
./.venv/bin/uvicorn main:app --reload --port 8000
```

**Frontend** (from `frontend/`):

```bash
npm run dev
```

The frontend runs at `http://localhost:5173` (`frontend/vite.config.ts`) and talks to the backend at `VITE_API_BASE_URL` (default `http://localhost:8000`). Visit `http://localhost:8000/health` to confirm `gemini_configured` and `supabase_configured` are both `true`.

## 8. API request and response example

### `GET /health`

```json
{
  "status": "ok",
  "gemini_configured": true,
  "supabase_configured": true
}
```

### `POST /analyze`

Request:

```json
{
  "customer_message": "my package says delivered but I never got it, where is it?",
  "brand": "AmazonHelp"
}
```

Response (evidence truncated to two of five items for brevity):

```json
{
  "intent": "delivery_delay_or_missing",
  "confidence": 0.95,
  "reply": "Thanks for reaching out to us. Here are some steps to try in situations like these: https://t.co/98Tpfm6ZUO ^GG",
  "decision": "escalate",
  "reason": "The customer is reporting a missing package marked as delivered, which matches the exact scenario and resolution provided in evidence [3]. (escalated: the package is reported missing or stolen, or marked delivered but not received — this needs human verification of the delivery or account rather than an automatic reply, since strong similarity to a past case doesn't confirm what actually happened to THIS shipment.)",
  "evidence": [
    {
      "id": "twcs-494861-494860",
      "customer_text": "Hi I ordered a parcel today order number #204-0948754-5997120 + #204-8409226-0967504 and it says it was delivered to a neighbour but the neighbour claims they don't have it despite me receiving an email claiming it had?",
      "agent_reply": "I'm sorry for the trouble with your delivery. We'd like to take a closer look at what's happened here: https://t.co/JzP7hlA23B ^RA",
      "similarity": 0.606
    },
    {
      "id": "twcs-1050778-1050777",
      "customer_text": "my package says delivered but never got it. Where is my package !!!!",
      "agent_reply": "Thanks for reaching out to us. Here are some steps to try in situations like these: https://t.co/98Tpfm6ZUO ^GG",
      "similarity": 0.557
    }
  ],
  "safety_checks": {
    "grounded_in_evidence": true,
    "invents_policy": false,
    "invents_refund_or_compensation": false,
    "invents_delivery_date": false,
    "invents_account_action": false,
    "contains_pii": false
  }
}
```

This is a real, unedited response from a running instance (evidence list shortened for length).

## 9. UI states

- **Empty (welcome)** — before any message is sent: logo, subtitle, heading, composer, and four quick-fill example buttons (`frontend/src/components/WelcomeScreen.tsx`, `ExampleButtons.tsx`).
- **Loading** — while a request is in flight, the turn shows a plain "Analyzing…" text placeholder (no card styling) below the customer's message bubble.
- **Success** — the full analysis card: intent, confidence, suggested reply (with a "Copy reply" button), decision badge (`Auto-handle` / `Escalate to human`), the reason, and two collapsible sections — "Historical evidence" and "Safety checks".
  - **Empty evidence sub-state** — if no similar conversations were retrieved, the evidence panel reads "No similar past conversations were found." instead of a list.
- **Error** — if the request fails (network error or non-2xx response), that turn shows an inline error message; other turns in the conversation are unaffected.

The composer stays pinned to the bottom of the screen once a conversation has started, and the brand header animates from a centered welcome position to a compact top-left bar on the first submit.

## 10. Safety and grounding

The suggested reply is a **draft for a human agent** — SupportLens never sends a reply to a customer itself. It is shown for review, is fully editable in principle (rendered as plain text, with a copy-to-clipboard action), and the `decision` field is a recommendation, not an automatic action.

**High similarity to a past case is not sufficient to auto-handle.** On top of the model's own `auto_handle`/`escalate` decision, three deterministic overrides in `backend/agent.py` can only push a case toward `escalate`, never the reverse:

1. **Weak evidence** — if no retrieved conversation reaches `MIN_EVIDENCE_SIMILARITY` (0.5), the case is escalated regardless of what the model decided.
2. **Categorical sensitivity** — a fixed keyword match (`CATEGORICAL_ESCALATION_RULES`) forces escalation regardless of similarity for: account security (hacked/compromised/fraud), billing or payment disputes, **missing or stolen packages — including a package marked "delivered" that the customer says they never received**, refund requests, and legal concerns. For these, a close historical match doesn't confirm what actually happened to *this* customer's shipment or account, so it always goes to a human.
3. **Failed self-reported safety checks** — if the model's own safety checklist (`SafetyChecks`) indicates the drafted reply isn't grounded in evidence, or invents a policy, refund, delivery date, or account action, the case is escalated even if the model itself proposed `auto_handle`.

The safety-check fields default to the "unsafe" value when missing from the model's response, so an incomplete or malformed self-report fails safe rather than silently passing.

## 11. Error handling

- **Missing `GEMINI_API_KEY`**: `/analyze` returns a fallback response (`decision: "escalate"`, a generic holding reply, `safety_checks.fallback: true`) instead of calling Gemini.
- **Gemini API call fails** (network error, quota, invalid model name): caught, logged to `evaluation/results/validation_failures.jsonl`, and the same safe fallback is returned.
- **Gemini responds with invalid structured output** (fails Pydantic validation — wrong types, an intent outside the closed taxonomy, an out-of-range confidence, malformed JSON): caught, logged with the raw response, and the safe fallback is returned rather than trusting unvalidated output.
- **Retrieval fails** (Supabase or Pinecone error): caught in `agent.py`, degrading to an empty evidence list rather than crashing the request.
- **Any other uncaught exception** in `/analyze`: FastAPI returns `500` with a generic `"Failed to analyze message"` detail — internal error details are never leaked to the client.
- **Frontend request failure** (network error or non-2xx response): `frontend/src/api.ts` throws, and `App.tsx` records the error on that turn only, showing an inline error message without disrupting the rest of the conversation.

## 12. Known limitations

- **Single hardcoded brand.** The frontend always sends `brand: "AmazonHelp"` (`DEFAULT_BRAND` in `App.tsx`); there is no brand selector.
- **Closed, fixed intent taxonomy.** The 12 intents in `backend/intents.py` are not configurable at runtime; anything that doesn't fit is classified `other` or `general_inquiry`.
- **No persistence of results.** `backend/db/database.py` defines `save_prediction()` and the `predictions` table (for auditing), but `/analyze` does not currently call it — analysis results are not stored.
- **The `intents` table is unused.** `backend/db/database.py` defines `load_intent_definitions()` to read intent descriptions from Supabase, but the app currently reads the taxonomy from `backend/intents.py` in code, not from that table.
- **No authentication.** `/analyze` and `/health` are open endpoints; access control is left to deployment-level configuration (e.g. `FRONTEND_ORIGIN` CORS restriction only).
- **Evidence retrieval only, no reranking.** The top-K results from `match_conversations` are used as-is; there is no secondary reranking step.
- **English-language assumption.** Intent definitions and the categorical keyword rules are written for English customer messages.

## 13. Future improvements

- Persist every `/analyze` result via the existing `save_prediction()` function for auditing and offline evaluation.
- Support multiple brands, with per-brand intent taxonomies loaded from the (currently unused) `intents` table.
- Add authentication/authorization in front of the API for production use.
- Add a reranking step over retrieved evidence before it's passed to the model.
- Surface the evaluation suite's results (see `evaluation/README.md`) in CI to catch regressions in intent accuracy, escalation precision/recall, or retrieval quality.

## 14. Contributing

This is an assignment project. If you're extending it:

- Keep `backend/db/database.py` as the only module that talks to the Supabase client directly (see its module docstring).
- Don't loosen `LLMDecision`'s Pydantic validation to work around a bad model response — fix the prompt or taxonomy, and let invalid responses fall back safely.
- New escalation-relaxing logic should not bypass the existing safety overrides in `backend/agent.py` — they are intentionally one-directional (`auto_handle` → `escalate` only).
- Before submitting changes, at minimum run `npm run build` in `frontend/` (type-checks and builds) and `python -m py_compile *.py db/*.py` in `backend/`. Neither project currently has a configured lint (e.g. ESLint) or automated test suite (e.g. pytest) — `evaluation/` is a manual evaluation harness, not a test suite run in CI.

## 15. License

No license file is currently included in this repository. All rights are reserved by the author unless a license is added.

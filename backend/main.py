import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from agent import analyze_message

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

app = FastAPI(title="SupportLens API", version="0.1.0")

DEFAULT_FRONTEND_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
_frontend_origins = [
    origin.strip()
    for origin in os.environ.get("FRONTEND_ORIGIN", DEFAULT_FRONTEND_ORIGINS).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConversationTurn(BaseModel):
    customer_message: str
    agent_reply: str


class AnalyzeRequest(BaseModel):
    customer_message: str = Field(..., min_length=1, description="The incoming customer message.")
    brand: str = Field(..., min_length=1, description="The brand this conversation belongs to.")
    conversation_history: list[ConversationTurn] = Field(
        default=[], description="Prior turns of this same conversation, oldest first, for context only."
    )


class EvidenceItem(BaseModel):
    id: str
    customer_text: str
    agent_reply: str
    similarity: float


class AnalyzeResponse(BaseModel):
    intent: str
    confidence: float
    reply: str
    decision: str  # "auto_handle" | "escalate"
    reason: str
    evidence: list[EvidenceItem] = []
    safety_checks: dict = {}


@app.get("/health")
def health() -> dict:
    """Liveness check — reports whether services are configured, never the key values themselves."""
    return {
        "status": "ok",
        "gemini_configured": bool(os.environ.get("GEMINI_API_KEY")),
        "supabase_configured": bool(
            os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SECRET_KEY")
        ),
    }


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Runs the agent pipeline; falls back safely (see agent.py) if Gemini/Supabase aren't configured."""
    try:
        history = [turn.model_dump() for turn in request.conversation_history]
        result = analyze_message(request.customer_message, request.brand, conversation_history=history)
    except Exception as exc:  # defensive: never leak internals in the response
        raise HTTPException(status_code=500, detail="Failed to analyze message") from exc

    return AnalyzeResponse(**result)

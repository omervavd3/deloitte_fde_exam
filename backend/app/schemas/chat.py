from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.agent.state import Intent


class ConversationSummary(BaseModel):
    id: UUID
    title: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ConversationUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class ChatRequest(BaseModel):
    conversation_id: UUID
    message: str = Field(min_length=1, max_length=4000)
    weight_overrides: dict[str, float] | None = None


class WeightsUsed(BaseModel):
    profile: str
    weights: dict[str, float]
    overridden: bool = False


class AirportScore(BaseModel):
    iata: str
    name: str
    score: float
    rank: int
    # None where an airport has no value for a weighted metric - the optional
    # T-100 Segment metrics are missing for most small airports. Scoring
    # renormalizes over what is present; reporting the gap as null rather than
    # 0.0 keeps "no data" distinct from "measured zero".
    metrics: dict[str, float | None]


class ReasoningStep(BaseModel):
    """One decision the agent made before any number was computed.

    Read back out of state, not written by the LLM - except the profile
    rationale, which is quoted inside `detail` and attributed there.
    """

    step: str
    detail: str


class MethodNote(BaseModel):
    """How the ranking must be read. Computed, so the model cannot drop it."""

    topic: str
    detail: str


class LiveStatus(BaseModel):
    iata: str
    delay_reason: str | None = None
    aircraft_in_area: int | None = None


class ChatResponse(BaseModel):
    """Narration plus every number the frontend renders.

    `message` is LLM-written. Everything below it is computed.
    """

    conversation_id: UUID
    message: str
    intent: Intent
    scores: list[AirportScore] = []
    breakdown: dict[str, dict[str, float]] = {}
    reasoning: list[ReasoningStep] = []
    method_notes: list[MethodNote] = []
    weights_used: WeightsUsed | None = None
    live_conditions: list[LiveStatus] = []
    assumptions: list[str] = []
    warnings: list[str] = []
    provenance: dict[str, Any] = {}


class ConversationMessage(BaseModel):
    """A replayed turn. `turn` carries the numbers so the UI redraws the tables."""

    role: Literal["user", "assistant"]
    content: str
    turn: ChatResponse | None = None

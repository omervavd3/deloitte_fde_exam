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


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


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
    metrics: dict[str, float]


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
    weights_used: WeightsUsed | None = None
    live_conditions: list[LiveStatus] = []
    assumptions: list[str] = []
    warnings: list[str] = []
    provenance: dict[str, Any] = {}

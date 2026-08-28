from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

Intent = Literal["rank", "compare", "metric", "explain", "out_of_scope"]


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]

    # Set by the LLM (intent layer). Never numeric results.
    intent: Intent
    raw_entities: list[str]
    profile_name: str
    clarification: dict[str, Any] | None

    # Set by deterministic code.
    airports: list[str]
    region: str | None
    weights: dict[str, float]
    weight_overrides: dict[str, float] | None
    scores: list[dict[str, Any]]
    breakdown: dict[str, dict[str, float]]
    live_conditions: dict[str, Any]

    # Carried across turns for follow-ups.
    focus: list[str]
    assumptions: list[str]
    warnings: list[str]

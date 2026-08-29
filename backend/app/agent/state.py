from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

Intent = Literal[
    "rank", "compare", "metric", "explain", "answer", "chitchat", "out_of_scope"
]

# Rows a ranking shows by default, and the threshold above which a place-scoped
# query asks whether the user wants the top ones or all of them.
DEFAULT_RESULT_LIMIT = 10


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]

    # Set by the LLM (intent layer). Never numeric results.
    intent: Intent
    raw_entities: list[str]
    profile_name: str
    clarification: dict[str, Any] | None
    scope_answer: Literal["all", "top"] | None
    scope_count: int | None

    # Set by deterministic code.
    airports: list[str]
    region: str | None
    weights: dict[str, float]
    weight_overrides: dict[str, float] | None
    scores: list[dict[str, Any]]
    breakdown: dict[str, dict[str, float]]
    facts: dict[str, dict[str, Any]]
    live_conditions: list[dict[str, Any]]

    # Carried across turns for follow-ups.
    focus: list[str]
    pending_options: list[str]
    result_limit: int | None
    assumptions: list[str]
    warnings: list[str]

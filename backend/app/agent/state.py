from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from app.config import get_settings

_settings = get_settings()

Intent = Literal[
    "rank", "compare", "metric", "explain", "answer", "chitchat", "out_of_scope"
]

# Rows a ranking shows by default, and the threshold above which a place-scoped
# query asks whether the user wants the top ones or all of them.
DEFAULT_RESULT_LIMIT = _settings.default_result_limit

# How many times one clarification question may be asked before the agent
# proceeds on a stated assumption. Per question, not per turn.
MAX_CLARIFY_ROUNDS = _settings.max_clarify_rounds

# clarify_answered key for the "top ones or all of them?" question, which
# settles a row count rather than an airport. Cannot collide with a user term.
SCOPE_KEY = "__scope__"


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]

    # Set by the LLM (intent layer). Never numeric results.
    intent: Intent
    raw_entities: list[str]
    profile_name: str
    # The intent model's own sentence on why it picked that profile. Surfaced
    # verbatim and labelled as a machine justification, never as a fact.
    profile_rationale: str
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
    # How to read the ranking: normalization basis, unresolvable ties, rows
    # ranked on a reduced metric set, and what a high score cannot mean.
    # Computed in app.scoring.explain, never written by the LLM.
    method_notes: list[dict[str, str]]
    # What built each shown score: per-metric standing, points and separation
    # from the next row. Computed in app.scoring.drivers, also never the LLM's.
    drivers: list[dict[str, Any]]
    facts: dict[str, dict[str, Any]]
    live_conditions: list[dict[str, Any]]

    # The clarification loop: everything the turn could not pin down, asked one
    # question at a time. clarify_attempts counts asks of the queue head.
    clarify_queue: list[dict[str, Any]]
    clarify_answered: dict[str, list[str]]
    clarify_attempts: int

    # Carried across turns for follow-ups.
    focus: list[str]
    pending_options: list[str]
    result_limit: int | None
    assumptions: list[str]
    warnings: list[str]


def cleared_results() -> dict[str, Any]:
    """Wipe the previous turn's numbers.

    State is carried across turns by the checkpointer, so a turn that skips
    scoring would otherwise answer with the last ranking still attached.
    """
    return {
        "scores": [],
        "breakdown": {},
        "method_notes": [],
        "drivers": [],
        "live_conditions": [],
        "weights": {},
        "assumptions": [],
    }

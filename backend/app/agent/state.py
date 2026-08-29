from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

Intent = Literal[
    "rank", "compare", "metric", "explain", "answer", "chitchat", "out_of_scope"
]

# Rows a ranking shows by default, and the threshold above which a place-scoped
# query asks whether the user wants the top ones or all of them.
DEFAULT_RESULT_LIMIT = 10

# How many times one clarification question may be asked before the agent stops
# asking and proceeds on a stated assumption. The budget is per question, not
# per turn: an answer that lands resets it for the next thing in the queue.
MAX_CLARIFY_ROUNDS = 3

# clarify_answered key for the "top ones or all of them?" question, which
# settles a row count rather than an airport. Cannot collide with a term the
# user typed.
SCOPE_KEY = "__scope__"


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

    # The clarification loop. Everything the turn could not pin down is queued
    # and asked one question at a time; clarify_answered accumulates the picks
    # so far, and clarify_attempts counts how many times the question at the
    # head of the queue has been asked.
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

    The checkpointer carries state across turns, so a turn that skips scoring
    would otherwise answer with the last ranking still attached.
    """
    return {
        "scores": [],
        "breakdown": {},
        "live_conditions": [],
        "weights": {},
        "assumptions": [],
    }

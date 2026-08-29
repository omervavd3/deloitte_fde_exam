import json
from typing import Literal

from langchain_core.messages import SystemMessage
from pydantic import BaseModel, Field

from app.agent.deps import Deps
from app.agent.prompts import INTENT_SYSTEM, PENDING_BLOCK, PENDING_NONE
from app.agent.state import AgentState, Intent
from app.scoring.profiles import FALLBACK_PROFILE
from app.services.profile_service import profile_catalog

# Recent turns handed to the model so a short reply ("all of them") is read in
# context. Without this the classifier sees a bare fragment and falls back to
# out_of_scope.
HISTORY_MESSAGES = 6


class IntentResult(BaseModel):
    """Schema the model fills in. Descriptions here reach the LLM.

    with_structured_output serialises this to a JSON schema and sends it as a
    tool definition, so each field's description is part of the instruction.
    """

    intent: Intent = Field(
        description="What the question asks for. Use 'out_of_scope' for cost, "
        "ROI, financing or political questions this system has no data for. "
        "Never use it for a short reply that answers a pending question."
    )
    entities: list[str] = Field(
        default_factory=list,
        description="Airport or city names mentioned, verbatim and one per "
        "string. Do not expand to IATA codes; resolution happens downstream. "
        "State names belong in 'region', not here.",
    )
    region: str | None = Field(
        default=None,
        description="A US state or named multi-state region if the question "
        "mentions one, e.g. 'Oregon' or 'New England'. Null when none is named.",
    )
    profile: str = Field(
        description="Name of the weight profile whose description best matches "
        "what the question cares about, or 'none_fit' when none clearly applies."
    )
    scope_count: int | None = Field(
        default=None,
        description="How many airports the user asked to see, whenever they "
        "name a number - 'the top 5', 'just 3', 'show me 20'. Use the number "
        "they asked for, not one offered to them. Null when no number is given.",
    )
    scope_answer: Literal["all", "top"] | None = Field(
        default=None,
        description="Set when the user says how much to cover without naming a "
        "number: 'all' when they want every airport offered, 'top' when they "
        "want just the leading ones. Null otherwise.",
    )
    reasoning: str = Field(
        default="", description="One sentence on why that profile was chosen."
    )


async def parse_intent(deps: Deps, state: AgentState) -> dict:
    """LLM: question -> intent, entity strings, profile name. No numbers."""
    catalog = await profile_catalog(deps.pool)
    pending = state.get("pending_options") or []
    system = INTENT_SYSTEM.format(
        profiles=json.dumps(catalog, indent=2),
        pending=PENDING_BLOCK.format(options=", ".join(pending))
        if pending
        else PENDING_NONE,
    )

    # Send recent history, not just the last message: a reply like "all of
    # them" is meaningless without the question it answers.
    history = state["messages"][-HISTORY_MESSAGES:]
    result: IntentResult = await deps.llm.with_structured_output(IntentResult).ainvoke(
        [SystemMessage(system), *history]
    )

    known = {p["name"] for p in catalog}
    profile = result.profile if result.profile in known else FALLBACK_PROFILE
    assumptions = []
    if result.profile not in known:
        assumptions.append(
            f"no profile matched this question; used the {FALLBACK_PROFILE} default"
        )

    return {
        "intent": result.intent,
        "raw_entities": result.entities,
        "region": result.region,
        "profile_name": profile,
        # Kept rather than discarded: the profile choice moves the ranking more
        # than any weight does, and this is the only record of why it was made.
        "profile_rationale": result.reasoning if result.profile in known else "",
        "scope_answer": result.scope_answer,
        "scope_count": result.scope_count,
        "assumptions": assumptions,
        "clarification": None,
        "warnings": [],
    }

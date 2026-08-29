import json

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agent.deps import Deps
from app.agent.prompts import INTENT_SYSTEM
from app.agent.state import AgentState, Intent
from app.scoring.profiles import FALLBACK_PROFILE
from app.services.profile_service import profile_catalog


class IntentResult(BaseModel):
    """Schema the model fills in. Descriptions here reach the LLM.

    with_structured_output serialises this to a JSON schema and sends it as a
    tool definition, so each field's description is part of the instruction.
    """

    intent: Intent = Field(
        description="What the question asks for. Use 'out_of_scope' for cost, "
        "ROI, financing or political questions this system has no data for."
    )
    entities: list[str] = Field(
        default_factory=list,
        description="Airport or city names mentioned, verbatim and one per "
        "string. Do not expand to IATA codes; resolution happens downstream.",
    )
    region: str | None = Field(
        default=None,
        description="A named multi-state region if the question mentions one, "
        "e.g. 'New England'. Null when no region is named.",
    )
    profile: str = Field(
        description="Name of the weight profile whose description best matches "
        "what the question cares about, or 'none_fit' when none clearly applies."
    )
    reasoning: str = Field(
        default="", description="One sentence on why that profile was chosen."
    )


async def parse_intent(deps: Deps, state: AgentState) -> dict:
    """LLM: question -> intent, entity strings, profile name. No numbers."""
    catalog = await profile_catalog(deps.pool)
    system = INTENT_SYSTEM.format(profiles=json.dumps(catalog, indent=2))

    question = state["messages"][-1].content
    result: IntentResult = await deps.llm.with_structured_output(IntentResult).ainvoke(
        [SystemMessage(system), HumanMessage(question)]
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
        "assumptions": assumptions,
        "clarification": None,
        "warnings": [],
    }

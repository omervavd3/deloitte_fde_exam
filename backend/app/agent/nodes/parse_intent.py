import json

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agent.deps import Deps
from app.agent.prompts import INTENT_SYSTEM
from app.agent.state import AgentState, Intent
from app.scoring.profiles import FALLBACK_PROFILE
from app.services.profile_service import profile_catalog


class IntentResult(BaseModel):
    intent: Intent
    entities: list[str] = Field(default_factory=list)
    region: str | None = None
    profile: str
    reasoning: str = ""


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

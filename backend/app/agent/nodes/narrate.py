import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.deps import Deps
from app.agent.prompts import CLARIFY_SYSTEM, NARRATE_SYSTEM, OUT_OF_SCOPE_SYSTEM
from app.agent.state import AgentState


def _question(state: AgentState) -> str:
    return state["messages"][-1].content


async def narrate(deps: Deps, state: AgentState) -> dict:
    """LLM: explain the computed results. May only restate numbers in state."""
    if state.get("clarification"):
        payload = json.dumps(state["clarification"], indent=2)
        response = await deps.llm.ainvoke(
            [SystemMessage(CLARIFY_SYSTEM), HumanMessage(payload)]
        )
        return {"messages": [response]}

    if state.get("intent") == "out_of_scope":
        response = await deps.llm.ainvoke(
            [SystemMessage(OUT_OF_SCOPE_SYSTEM), HumanMessage(_question(state))]
        )
        return {"messages": [response]}

    context = json.dumps(
        {
            "question": _question(state),
            "profile": state.get("profile_name"),
            "weights": state.get("weights"),
            "scores": state.get("scores", []),
            "score_breakdown": state.get("breakdown", {}),
            "live_conditions": state.get("live_conditions", []),
            "assumptions": state.get("assumptions", []),
            "warnings": state.get("warnings", []),
        },
        indent=2,
        default=str,
    )

    response = await deps.llm.ainvoke(
        [SystemMessage(NARRATE_SYSTEM), HumanMessage(context)]
    )
    return {"messages": [response]}

import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.deps import Deps
from app.agent.nodes.load_facts import FACT_COLUMNS
from app.agent.prompts import (
    ANSWER_SYSTEM,
    CHITCHAT_SYSTEM,
    CLARIFY_AIRPORTS_SYSTEM,
    CLARIFY_SCOPE_SYSTEM,
    NARRATE_SYSTEM,
    OUT_OF_SCOPE_SYSTEM,
)
from app.agent.state import AgentState
from app.agent.trace import reasoning_steps
from app.scoring.glossary import glossary_for


# Recent turns, so a reply to a clarification ("1", "all of them") is read
# against the question it answers rather than as a question of its own.
HISTORY_MESSAGES = 6


def _question(state: AgentState) -> str:
    return state["messages"][-1].content


def _history(state: AgentState) -> list:
    return state["messages"][-HISTORY_MESSAGES:]


def _turn(state: AgentState) -> dict:
    """The computed half of a turn: everything the UI renders below the prose."""
    weights = state.get("weights")
    return {
        "intent": state.get("intent", "explain"),
        "scores": state.get("scores", []),
        "breakdown": state.get("breakdown", {}),
        # Both transparency channels are computed, so they survive whatever the
        # model chose to say.
        "reasoning": reasoning_steps(state),
        "method_notes": state.get("method_notes", []),
        "weights_used": {
            "profile": state.get("profile_name", ""),
            "weights": weights,
            "overridden": bool(state.get("weight_overrides")),
        }
        if weights
        else None,
        "live_conditions": state.get("live_conditions", []),
        "assumptions": state.get("assumptions", []),
        "warnings": state.get("warnings", []),
    }


def _answer(state: AgentState, response) -> dict:
    """Pin the turn's numbers to the message that narrates them.

    additional_kwargs rides the checkpoint, so replaying a thread rebuilds the
    tables too - state alone only holds the *last* turn's results. It never
    reaches the LLM, which drops unrecognised additional_kwargs.
    """
    response.additional_kwargs["turn"] = _turn(state)
    return {"messages": [response]}


async def narrate(deps: Deps, state: AgentState) -> dict:
    """LLM: explain the computed results. May only restate numbers in state."""
    clarification = state.get("clarification")
    if clarification:
        system = (
            CLARIFY_SCOPE_SYSTEM
            if clarification.get("kind") == "scope"
            else CLARIFY_AIRPORTS_SYSTEM
        )
        payload = json.dumps(clarification, indent=2)
        response = await deps.llm.ainvoke([SystemMessage(system), HumanMessage(payload)])
        return _answer(state, response)

    # Small talk: no payload, just the conversation.
    if state.get("intent") == "chitchat":
        response = await deps.llm.ainvoke(
            [SystemMessage(CHITCHAT_SYSTEM), *_history(state)]
        )
        return _answer(state, response)

    if state.get("intent") == "out_of_scope":
        response = await deps.llm.ainvoke(
            [SystemMessage(OUT_OF_SCOPE_SYSTEM), HumanMessage(_question(state))]
        )
        return _answer(state, response)

    # Direct question: the stored rows for the named airports and nothing else,
    # so there is no ranking in context to describe.
    if state.get("intent") == "answer":
        payload = json.dumps(
            {
                "airports": state.get("facts", {}),
                "covered_metrics": FACT_COLUMNS,
                "warnings": state.get("warnings", []),
            },
            indent=2,
            default=str,
        )
        response = await deps.llm.ainvoke(
            [SystemMessage(ANSWER_SYSTEM), *_history(state), HumanMessage(payload)]
        )
        return _answer(state, response)

    context = json.dumps(
        {
            "profile": state.get("profile_name"),
            "profile_rationale": state.get("profile_rationale", ""),
            "weights": state.get("weights"),
            # A pure lookup, so it is resolved here rather than held in state.
            "metric_glossary": glossary_for(state.get("weights") or {}),
            "scores": state.get("scores", []),
            "score_breakdown": state.get("breakdown", {}),
            "score_drivers": state.get("drivers", []),
            "method_notes": state.get("method_notes", []),
            "live_conditions": state.get("live_conditions", []),
            "assumptions": state.get("assumptions", []),
            "warnings": state.get("warnings", []),
        },
        indent=2,
        default=str,
    )

    response = await deps.llm.ainvoke(
        [SystemMessage(NARRATE_SYSTEM), *_history(state), HumanMessage(context)]
    )
    return _answer(state, response)

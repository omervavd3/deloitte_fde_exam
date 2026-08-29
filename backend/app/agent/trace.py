"""The turn's decision chain, read back out of state.

Trust in a ranking is not only trust in its arithmetic. Before any number was
computed the agent decided what the question meant, which investment thesis to
score it under, and how much of the region to cover - and each of those choices
changes the answer more than the weights do. Every one is already recorded in
state; none of it was visible.

Assembled from state rather than written by the model, with one exception:
`profile_rationale` is the intent model's own sentence explaining its profile
choice, and is labelled as such so a reader knows which line is a machine
justification and which are facts about what ran.
"""

from dataclasses import dataclass
from typing import Any

from app.agent.state import AgentState

INTENT_READING = {
    "rank": "rank airports against each other",
    "compare": "compare named airports",
    "metric": "report a specific metric",
    "explain": "explain a result",
    "answer": "answer a direct question about named airports",
    "chitchat": "reply conversationally",
    "out_of_scope": "explain what falls outside the data",
}


@dataclass
class ReasoningStep:
    step: str
    detail: str


def _interpretation(state: AgentState) -> ReasoningStep:
    reading = INTENT_READING.get(state.get("intent", ""), "answer the question")
    scope = state.get("region") or ", ".join(state.get("raw_entities") or [])
    return ReasoningStep(
        "Read the question as",
        f"{reading}" + (f", scoped to {scope}" if scope else ""),
    )


def _profile(state: AgentState) -> ReasoningStep | None:
    name = state.get("profile_name")
    if not name:
        return None

    detail = f"{name}"
    if state.get("weight_overrides"):
        detail += ", with weights overridden for this turn"
    rationale = (state.get("profile_rationale") or "").strip()
    if rationale:
        detail += f". Chosen because: {rationale}"
    return ReasoningStep("Scored under the profile", detail)


def _scope(state: AgentState) -> ReasoningStep | None:
    considered = len(state.get("airports") or [])
    shown = len(state.get("scores") or [])
    if not considered:
        return None

    if shown and shown < considered:
        detail = (
            f"{considered} airports matched; showing the top {shown}. "
            f"All {considered} were scored - the rest are below the cut, "
            f"not excluded from the comparison."
        )
    else:
        detail = f"{considered} airports matched and all of them are shown."
    return ReasoningStep("Set the scope to", detail)


def _weighting(state: AgentState) -> ReasoningStep | None:
    weights = {m: w for m, w in (state.get("weights") or {}).items() if w > 0}
    if not weights:
        return None

    listed = ", ".join(
        f"{m} {w:.0%}"
        for m, w in sorted(weights.items(), key=lambda kv: -kv[1])
    )
    return ReasoningStep(
        "Weighted the metrics",
        f"{listed}. Each is percentile-ranked nationally, then blended at "
        f"these weights - so the score moves with an airport's standing "
        f"against every other airport, not with the raw metric value.",
    )


def _live(state: AgentState) -> ReasoningStep | None:
    live = state.get("live_conditions") or []
    if not live:
        return None
    return ReasoningStep(
        "Checked live conditions for",
        f"{len(live)} airport{'' if len(live) == 1 else 's'}. Advisory only - "
        f"FAA status and aircraft counts are shown beside the ranking but "
        f"never enter the score.",
    )


def reasoning_steps(state: AgentState) -> list[dict[str, Any]]:
    """The chain in the order the graph walked it."""
    steps = [
        _interpretation(state),
        _profile(state),
        _scope(state),
        _weighting(state),
        _live(state),
    ]
    return [{"step": s.step, "detail": s.detail} for s in steps if s]

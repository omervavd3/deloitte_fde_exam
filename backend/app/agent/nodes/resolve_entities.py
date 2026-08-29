from app.agent.deps import Deps
from app.agent.state import AgentState
from app.services.airport_service import resolve
from app.services.region_service import resolve_region


def _cleared_results() -> dict:
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


async def resolve_entities(deps: Deps, state: AgentState) -> dict:
    """Deterministic: entity strings -> IATA codes / region.

    Sets clarification when a name like 'LA' maps to several airports.
    """
    if state.get("intent") == "out_of_scope":
        return _cleared_results()

    metrics = deps.provider.get_metrics()
    region_codes = resolve_region(state["region"]) if state.get("region") else None

    result = resolve(state.get("raw_entities", []), metrics)

    if result.ambiguous:
        options = {
            term: [
                {"iata": code, "name": metrics.loc[code, "name"]}
                for code in codes
                if code in metrics.index
            ]
            for term, codes in result.ambiguous.items()
        }
        return {
            **_cleared_results(),
            "clarification": options,
            "airports": result.resolved,
            "warnings": [],
        }

    airports = result.resolved
    warnings = state.get("warnings", []) + [
        f"could not resolve: {term}" for term in result.unresolved
    ]

    # "How does it compare to Oakland?" names one airport but means two.
    # Carry the previous turn's focus so follow-ups keep their subject.
    previous = state.get("focus") or []
    if state.get("intent") == "compare" and len(airports) < 2 and previous:
        carried = [c for c in previous[:2] if c not in airports]
        if carried:
            airports = airports + carried
            warnings.append(f"carried forward from previous turn: {', '.join(carried)}")

    if not airports and region_codes:
        airports = metrics.index[metrics["iso_region"].isin(region_codes)].tolist()

    if not airports and not region_codes:
        # No entities and no region: fall back to a national ranking.
        airports = metrics.index.tolist()

    return {
        "airports": airports,
        "region": state.get("region"),
        "warnings": warnings,
        "clarification": None,
    }

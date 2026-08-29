from app.agent.deps import Deps
from app.agent.state import DEFAULT_RESULT_LIMIT, AgentState
from app.services.airport_service import AMBIGUOUS_NAMES, resolve
from app.services.region_service import is_place, resolve_region

# A place holding more airports than a ranking shows gets a scope question
# rather than a silent truncation to the top few.
SCOPE_ASK_ABOVE = DEFAULT_RESULT_LIMIT


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


def _ask(clarification: dict, offered: list[str]) -> dict:
    """Short-circuit to narrate with a question, remembering what was offered.

    pending_options is what "all of them" will mean next turn.
    """
    return {
        **_cleared_results(),
        "clarification": clarification,
        "airports": offered,
        "pending_options": offered,
        "result_limit": None,
        "warnings": [],
    }


def _limit(state: AgentState, total: int) -> int | None:
    """How many rows the user asked for, or None for the default.

    A number always wins over "all"/"top": someone who says "top 5" gets 5,
    whether they were answering a scope question or asked outright.
    """
    requested = state.get("scope_count")
    if requested:
        return max(1, min(int(requested), total))
    if state.get("scope_answer") == "all":
        return total or None
    return None


def _scopes(state: AgentState) -> tuple[list[str], list[str], list[str]]:
    """Split the turn's place references from its airport references.

    A term that names a metro area with several airports (LA, Washington) stays
    an airport reference so it still gets a clarification, even though it also
    resolves as a place.
    """
    terms = [state["region"]] if state.get("region") else []
    names: list[str] = []
    for term in state.get("raw_entities", []):
        if is_place(term) and term.strip().lower() not in AMBIGUOUS_NAMES:
            terms.append(term)
        else:
            names.append(term)

    codes: list[str] = []
    unknown: list[str] = []
    for term in terms:
        found = resolve_region(term)
        if found:
            codes.extend(found)
        else:
            unknown.append(term)
    return list(dict.fromkeys(codes)), names, unknown


async def resolve_entities(deps: Deps, state: AgentState) -> dict:
    """Deterministic: the question's text -> the airports we are going to score.

    Three ways out: answer a pending question, ask one, or hand a resolved set
    of airports to load_metrics.
    """
    if state.get("intent") == "out_of_scope":
        return {**_cleared_results(), "pending_options": [], "result_limit": None}

    # Small talk: nothing to resolve. Clear the numbers so no table renders,
    # but leave pending_options alone - a greeting in the middle of a
    # clarification should not throw away the question still waiting.
    if state.get("intent") == "chitchat":
        return {**_cleared_results(), "result_limit": None}

    metrics = deps.provider.get_metrics()
    pending = state.get("pending_options") or []

    # The user is answering the question we asked last turn.
    if pending and (state.get("scope_answer") or state.get("scope_count")):
        return {
            "airports": pending,
            "result_limit": _limit(state, len(pending)),
            "clarification": None,
            "pending_options": [],
            "warnings": [],
        }

    region_codes, names, unknown_places = _scopes(state)
    result = resolve(names, metrics)

    warnings = [f"unrecognized region: {term}" for term in unknown_places]
    warnings += [f"could not resolve: {term}" for term in result.unresolved]

    # A name like "LA" covers several airports. Offer them, plus all of them.
    if result.ambiguous:
        options = {
            term: [
                {"iata": code, "name": metrics.loc[code, "name"]}
                for code in codes
                if code in metrics.index
            ]
            for term, codes in result.ambiguous.items()
        }
        offered = [entry["iata"] for opts in options.values() for entry in opts]
        return _ask({"kind": "airports", "options": options}, offered)

    airports = result.resolved

    # "How does it compare to Oakland?" names one airport but means two.
    # Carry the previous turn's focus so follow-ups keep their subject.
    previous = state.get("focus") or []
    if state.get("intent") == "compare" and len(airports) < 2 and previous:
        carried = [c for c in previous[:2] if c not in airports]
        if carried:
            airports = airports + carried
            warnings.append(f"carried forward from previous turn: {', '.join(carried)}")

    scoped_by_place = False
    if not airports and region_codes:
        airports = metrics.index[metrics["iso_region"].isin(region_codes)].tolist()
        scoped_by_place = True
        if not airports:
            warnings.append("no airports with traffic data in that region")

    if not airports and not region_codes:
        # No entities and no region: fall back to a national ranking.
        airports = metrics.index.tolist()

    limit = _limit(state, len(airports))
    direct = state.get("intent") == "answer"

    # A state or region with more airports than we would show: ask rather than
    # truncate silently. A bare national ranking is left alone - "rank US
    # airports for cargo" already means "the top ones" - and so is a question
    # that already said how many it wants, or a direct question, which wants a
    # fact rather than a list of any length.
    if scoped_by_place and limit is None and not direct and len(airports) > SCOPE_ASK_ABOVE:
        label = state.get("region") or "that region"
        clarification = {
            "kind": "scope",
            "label": label,
            "count": len(airports),
            "top": SCOPE_ASK_ABOVE,
        }
        return _ask(clarification, airports)

    return {
        # A direct question skips score, so nothing downstream overwrites the
        # previous turn's ranking - clear it here or the answer arrives with a
        # stale table attached.
        **(_cleared_results() if direct else {}),
        "airports": airports,
        "region": state.get("region"),
        "warnings": warnings,
        "clarification": None,
        "pending_options": [],
        "result_limit": limit,
    }

from app.agent.deps import Deps
from app.agent.state import (
    DEFAULT_RESULT_LIMIT,
    SCOPE_KEY,
    AgentState,
    cleared_results,
)
from app.services.airport_service import AMBIGUOUS_NAMES, resolve
from app.services.region_service import is_place, resolve_region

# Above this many airports, a place-scoped query asks how much to cover rather
# than truncating silently.
SCOPE_ASK_ABOVE = DEFAULT_RESULT_LIMIT


def _limit(state: AgentState, total: int) -> int | None:
    """How many rows the user asked for, or None for the default.

    An explicit number always wins over "all"/"top".
    """
    requested = state.get("scope_count")
    if requested:
        return max(1, min(int(requested), total))
    if state.get("scope_answer") == "all":
        return total or None
    return None


def _scopes(state: AgentState) -> tuple[list[str], list[str], list[str]]:
    """Split the turn's references into (region codes, airport names, unknown places).

    A term naming a metro area with several airports (LA, Washington) stays an
    airport reference so it still gets a clarification, even though it also
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

    Three ways out: hand a resolved set of airports to load_metrics, queue what
    could not be pinned down for clarify to ask about, or - for a question with
    nothing to resolve - fall straight through to narrate.

    clarify loops back here once its queue is empty, so this runs a second time
    with clarify_answered filled in. Terms answered there are not re-resolved,
    which is what stops the loop.
    """
    if state.get("intent") == "out_of_scope":
        return {
            **cleared_results(),
            "pending_options": [],
            "result_limit": None,
            "clarify_queue": [],
            "clarify_answered": {},
            "clarify_attempts": 0,
        }

    # Small talk has nothing to resolve. The clarification queue is left alone:
    # a greeting mid-clarification is not a failed answer, so it costs no attempt.
    if state.get("intent") == "chitchat":
        return {**cleared_results(), "result_limit": None}

    # A question is outstanding: clarify owns this turn's message.
    if state.get("clarify_queue") and state.get("pending_options"):
        return {}

    metrics = deps.provider.get_metrics()
    answered = state.get("clarify_answered") or {}

    region_codes, names, unknown_places = _scopes(state)

    # Terms the user has already picked an airport for are settled; asking again
    # would loop forever.
    settled = [code for codes in answered.values() for code in codes]
    result = resolve([n for n in names if n.strip() not in answered], metrics)

    warnings = [f"unrecognized region: {term}" for term in unknown_places]
    warnings += [f"could not resolve: {term}" for term in result.unresolved]

    # One question per ambiguous name, so clarify can work through them in order.
    queue = [
        {
            "kind": "airports",
            "key": term,
            "term": term,
            # What the question was asked against, so clarify can tell a reply
            # that changes the subject from one that repeats it.
            "region": state.get("region"),
            "options": [
                {"iata": code, "name": metrics.loc[code, "name"]}
                for code in codes
                if code in metrics.index
            ],
        }
        for term, codes in result.ambiguous.items()
    ]

    airports = list(dict.fromkeys(settled + result.resolved))

    # "How does it compare to Oakland?" names one airport but means two: carry
    # the previous turn's focus so follow-ups keep their subject.
    previous = state.get("focus") or []
    if state.get("intent") == "compare" and not queue and len(airports) < 2 and previous:
        carried = [c for c in previous[:2] if c not in airports]
        if carried:
            airports = airports + carried
            warnings.append(f"carried forward from previous turn: {', '.join(carried)}")

    scoped_by_place = False
    if not airports and not queue and region_codes:
        airports = metrics.index[metrics["iso_region"].isin(region_codes)].tolist()
        scoped_by_place = True
        if not airports:
            warnings.append("no airports with traffic data in that region")

    if not airports and not queue and not region_codes:
        # No entities and no region: fall back to a national ranking.
        airports = metrics.index.tolist()

    limit = _limit(state, len(airports))
    direct = state.get("intent") == "answer"

    # Ask rather than truncate. A bare national ranking is left alone - "rank US
    # airports for cargo" already means "the top ones" - and so is a question
    # that already said how many it wants, or a direct question, which wants a
    # fact rather than a list of any length.
    if (
        scoped_by_place
        and limit is None
        and not direct
        and SCOPE_KEY not in answered
        and len(airports) > SCOPE_ASK_ABOVE
    ):
        queue.append(
            {
                "kind": "scope",
                "key": SCOPE_KEY,
                "region": state.get("region"),
                "label": state.get("region") or "that region",
                "count": len(airports),
                "top": SCOPE_ASK_ABOVE,
                "options": [{"iata": code, "name": ""} for code in airports],
            }
        )

    if queue:
        return {
            **cleared_results(),
            "clarify_queue": queue,
            "clarify_answered": answered,
            "result_limit": None,
            "warnings": warnings,
        }

    return {
        # A direct question skips score, so clear the previous turn's ranking
        # here or the answer arrives with a stale table attached. The
        # clarification's assumptions are kept: they explain airports the user
        # never actually picked.
        **({**cleared_results(), "assumptions": state.get("assumptions") or []}
           if direct else {}),
        "airports": airports,
        "region": state.get("region"),
        "warnings": warnings,
        "clarification": None,
        "pending_options": [],
        "result_limit": limit,
        # One clarification episode, one set of answers. Keeping them would
        # silently reuse an old choice of "LA" for a later, unrelated question.
        "clarify_queue": [],
        "clarify_answered": {},
        "clarify_attempts": 0,
    }

"""The clarification loop: ask about one unclear thing at a time.

resolve_entities queues everything the turn could not pin down. This node asks
about the head of that queue, reads the reply on the next turn, and loops back
to resolve_entities once nothing is left to ask.

The budget is per question, not per conversation: an answer that lands pops the
queue and gives the next question a fresh MAX_CLARIFY_ROUNDS asks. Once a
question's asks are gone the agent proceeds on an assumption it states out loud.
"""

from app.agent.deps import Deps
from app.agent.state import MAX_CLARIFY_ROUNDS, AgentState, cleared_results
from app.services.airport_service import resolve


def _codes(entry: dict) -> list[str]:
    return [option["iata"] for option in entry.get("options", [])]


def _read_answer(deps: Deps, state: AgentState, entry: dict) -> list[str] | None:
    """The reply, as airport codes - or None when it was not understood.

    An empty list is a valid answer: the scope question settles a row count,
    which resolve_entities re-derives from scope_answer/scope_count.
    """
    if entry["kind"] == "scope":
        settled = state.get("scope_answer") or state.get("scope_count")
        return [] if settled else None

    codes = _codes(entry)

    # "all of them" / "both": rank every airport that was offered.
    if state.get("scope_answer") == "all":
        return codes

    # A named airport, but only one of the ones we offered. Anything still
    # ambiguous - "Santa" again - is the same question over again, so it costs
    # an ask rather than settling one.
    entities = state.get("raw_entities") or []
    if entities:
        named = resolve(entities, deps.provider.get_metrics()).resolved
        picks = [code for code in named if code in codes]
        if picks:
            return picks

    # "the second one", "2": the options are numbered in the question we asked.
    position = state.get("scope_count")
    if position and 1 <= position <= len(codes):
        return [codes[position - 1]]

    return None


def _changed_subject(deps: Deps, state: AgentState, entry: dict) -> bool:
    """True when the reply asks something new instead of answering.

    Only consulted once the reply has failed to answer. A region only counts
    when it is a different one: the scope question is about a place, and a reply
    to it naturally repeats that place.
    """
    region = state.get("region")
    if region and region != entry.get("region"):
        return True
    entities = state.get("raw_entities") or []
    if not entities:
        return False
    named = resolve(entities, deps.provider.get_metrics()).resolved
    return bool(named) and not any(code in _codes(entry) for code in named)


def _give_up(entry: dict) -> tuple[list[str], str]:
    """What to assume when a question has used up its asks, and how to say so."""
    if entry["kind"] == "scope":
        return [], (
            f"asked {MAX_CLARIFY_ROUNDS} times how much of {entry['label']} to "
            f"cover without a clear answer; showed the top {entry['top']} of "
            f"{entry['count']}"
        )
    codes = _codes(entry)
    return codes, (
        f"asked {MAX_CLARIFY_ROUNDS} times which airport \"{entry['term']}\" "
        f"meant without a clear answer; included all candidates: "
        f"{', '.join(codes)}"
    )


def _question(entry: dict, attempt: int) -> dict:
    """The payload narrate turns into the question.

    A scope entry's options are every airport in the region - useful to us,
    nothing narrate is allowed to name - so they stay out of the prompt.
    """
    fields = (
        ("term", "options")
        if entry["kind"] == "airports"
        else ("label", "count", "top")
    )
    return {
        "kind": entry["kind"],
        **{name: entry[name] for name in fields},
        "attempt": attempt,
        "max_attempts": MAX_CLARIFY_ROUNDS,
        "remaining": MAX_CLARIFY_ROUNDS - attempt,
    }


def _ask(queue: list[dict], answered: dict, attempt: int, assumptions: list[str]) -> dict:
    """Put the head of the queue to the user and wait for the next turn.

    pending_options is both what "all of them" will mean next turn and the flag
    that says a question is outstanding.
    """
    entry = queue[0]
    offered = _codes(entry)
    return {
        **cleared_results(),
        "clarify_queue": queue,
        "clarify_answered": answered,
        "clarify_attempts": attempt,
        "clarification": _question(entry, attempt),
        "airports": offered,
        "pending_options": offered,
        "assumptions": assumptions,
        "result_limit": None,
        "warnings": [],
    }


async def clarify(deps: Deps, state: AgentState) -> dict:
    """Deterministic: read the reply to the pending question, ask the next one.

    Three ways out: ask (short-circuits to narrate), hand a settled set of
    answers back to resolve_entities, or drop the queue because the user changed
    the subject.
    """
    queue = list(state.get("clarify_queue") or [])
    answered = dict(state.get("clarify_answered") or {})
    assumptions = list(state.get("assumptions") or [])
    awaiting = bool(queue and state.get("pending_options"))
    attempts = (state.get("clarify_attempts") or 0) if awaiting else 0

    # A question is outstanding, so this turn's message is its answer.
    if awaiting:
        entry = queue[0]
        picked = _read_answer(deps, state, entry)

        if picked is None and _changed_subject(deps, state, entry):
            # Not an answer at all. Abandon the queue and let resolve_entities
            # start over on what was actually asked.
            return {
                "clarify_queue": [],
                "clarify_answered": {},
                "clarify_attempts": 0,
                "clarification": None,
                "pending_options": [],
            }

        if picked is None:
            if attempts < MAX_CLARIFY_ROUNDS:
                return _ask(queue, answered, attempts + 1, assumptions)
            # Out of asks: assume, say so, and move on to the next question.
            picked, note = _give_up(entry)
            assumptions.append(note)

        answered[entry["key"]] = picked
        queue.pop(0)
        attempts = 0

    # Understood: the next question starts with its full budget.
    if queue:
        return _ask(queue, answered, attempts + 1, assumptions)

    return {
        "clarify_queue": [],
        "clarify_answered": answered,
        "clarify_attempts": 0,
        "clarification": None,
        "pending_options": [],
        "assumptions": assumptions,
    }

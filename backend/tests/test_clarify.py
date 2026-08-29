"""The clarification loop, driven turn by turn.

The graph runs once per user message, so the loop spans turns: these tests
replay the router the compiled graph uses, feeding it what parse_intent would
have produced for each reply.
"""

from types import SimpleNamespace

import pandas as pd
import pytest

from app.agent.graph import _after_clarify, _after_resolve
from app.agent.nodes.clarify import clarify
from app.agent.nodes.resolve_entities import resolve_entities
from app.agent.state import MAX_CLARIFY_ROUNDS, SCOPE_KEY


@pytest.fixture
def deps(sample_metrics) -> SimpleNamespace:
    return SimpleNamespace(provider=SimpleNamespace(get_metrics=lambda: sample_metrics))


@pytest.fixture
def sample_metrics() -> pd.DataFrame:
    """Enough of the LA basin to make "LA" and "Santa" both ambiguous."""
    return pd.DataFrame(
        [
            {"iata": "LAX", "name": "Los Angeles International Airport",
             "municipality": "Los Angeles", "iso_region": "US-CA",
             "enplanement_volume": 26_000_000},
            {"iata": "BUR", "name": "Bob Hope Airport", "municipality": "Burbank",
             "iso_region": "US-CA", "enplanement_volume": 2_500_000},
            {"iata": "LGB", "name": "Long Beach Airport", "municipality": "Long Beach",
             "iso_region": "US-CA", "enplanement_volume": 1_300_000},
            {"iata": "ONT", "name": "Ontario International Airport",
             "municipality": "Ontario", "iso_region": "US-CA",
             "enplanement_volume": 2_600_000},
            {"iata": "SNA", "name": "John Wayne Airport-Orange County",
             "municipality": "Santa Ana", "iso_region": "US-CA",
             "enplanement_volume": 5_800_000},
            {"iata": "SBA", "name": "Santa Barbara Municipal Airport",
             "municipality": "Santa Barbara", "iso_region": "US-CA",
             "enplanement_volume": 900_000},
            {"iata": "SAF", "name": "Santa Fe Municipal Airport",
             "municipality": "Santa Fe", "iso_region": "US-NM",
             "enplanement_volume": 200_000},
            {"iata": "DEN", "name": "Denver International Airport",
             "municipality": "Denver", "iso_region": "US-CO",
             "enplanement_volume": 33_000_000},
        ]
    ).set_index("iata")


async def turn(deps, state: dict, **intent) -> tuple[dict, str]:
    """One user message through the graph, up to the node that ends the turn.

    Mirrors parse_intent's reset of the per-turn fields, then walks the same
    conditional edges the compiled graph walks.
    """
    state = {
        **state,
        "intent": "compare",
        "raw_entities": [],
        "region": None,
        "scope_answer": None,
        "scope_count": None,
        **intent,
        "clarification": None,
        "assumptions": [],
        "warnings": [],
    }

    node = "resolve_entities"
    for _ in range(10):
        if node == "resolve_entities":
            state = {**state, **await resolve_entities(deps, state)}
            node = _after_resolve(state)
        elif node == "clarify":
            state = {**state, **await clarify(deps, state)}
            node = _after_clarify(state)
        else:
            return state, node
    raise AssertionError("routing did not settle")


async def test_asks_about_one_name_at_a_time(deps):
    """"Compare LA and Santa" is two questions; only the first is asked."""
    state, node = await turn(deps, {}, raw_entities=["LA", "Santa"])

    assert node == "narrate"
    assert state["clarification"]["term"] == "LA"
    assert state["clarification"]["attempt"] == 1
    assert [q["term"] for q in state["clarify_queue"]] == ["LA", "Santa"]


async def test_understood_answer_moves_to_the_next_question(deps):
    state, _ = await turn(deps, {}, raw_entities=["LA", "Santa"])
    state, node = await turn(deps, state, raw_entities=["LAX"])

    assert node == "narrate"
    assert state["clarify_answered"] == {"LA": ["LAX"]}
    assert state["clarification"]["term"] == "Santa"
    # A fresh question gets the full budget back.
    assert state["clarification"]["attempt"] == 1


async def test_answer_by_position_in_the_offered_list(deps):
    state, _ = await turn(deps, {}, raw_entities=["LA", "Santa"])
    offered = [o["iata"] for o in state["clarification"]["options"]]

    state, _ = await turn(deps, state, scope_count=2)

    assert state["clarify_answered"] == {"LA": [offered[1]]}


async def test_all_of_them_takes_every_candidate(deps):
    state, _ = await turn(deps, {}, raw_entities=["LA"])
    offered = [o["iata"] for o in state["clarification"]["options"]]

    state, node = await turn(deps, state, scope_answer="all")

    assert node == "load_metrics"
    assert state["airports"] == offered


async def test_a_reply_it_cannot_read_asks_again(deps):
    state, _ = await turn(deps, {}, raw_entities=["LA", "Santa"])
    state, node = await turn(deps, state, raw_entities=["the beach one"])

    assert node == "narrate"
    assert state["clarification"]["term"] == "LA"
    assert state["clarification"]["attempt"] == 2
    assert state["clarify_answered"] == {}


async def test_gives_up_after_three_asks_and_says_so(deps):
    state, _ = await turn(deps, {}, raw_entities=["LA"])
    assert state["clarification"]["attempt"] == 1

    for expected in range(2, MAX_CLARIFY_ROUNDS + 1):
        state, node = await turn(deps, state, raw_entities=["no idea"])
        assert node == "narrate"
        assert state["clarification"]["attempt"] == expected

    # The budget is spent: assume every candidate and get on with the answer.
    state, node = await turn(deps, state, raw_entities=["still no idea"])

    assert node == "load_metrics"
    assert state["airports"] == ["LAX", "BUR", "LGB", "ONT", "SNA"]
    assert any("LA" in note for note in state["assumptions"])
    assert state["clarify_queue"] == []


async def test_an_understood_answer_resets_the_budget(deps):
    """The count is per question: two failures on LA cost Santa nothing."""
    state, _ = await turn(deps, {}, raw_entities=["LA", "Santa"])
    state, _ = await turn(deps, state, raw_entities=["dunno"])
    assert state["clarification"]["attempt"] == 2

    state, _ = await turn(deps, state, raw_entities=["LAX"])
    assert state["clarification"]["term"] == "Santa"
    assert state["clarification"]["attempt"] == 1

    state, _ = await turn(deps, state, raw_entities=["dunno"])
    assert state["clarification"]["attempt"] == 2


async def test_naming_the_city_answers_the_santa_question(deps):
    state, _ = await turn(deps, {}, raw_entities=["LA", "Santa"])
    state, _ = await turn(deps, state, raw_entities=["LAX"])

    state, node = await turn(deps, state, raw_entities=["Santa Ana"])

    assert node == "load_metrics"
    assert state["airports"] == ["LAX", "SNA"]
    assert state["clarify_answered"] == {}


async def test_repeating_the_ambiguous_name_is_not_an_answer(deps):
    state, _ = await turn(deps, {}, raw_entities=["Santa"])
    state, node = await turn(deps, state, raw_entities=["Santa"])

    assert node == "narrate"
    assert state["clarification"]["attempt"] == 2


async def test_changing_the_subject_drops_the_queue(deps):
    state, _ = await turn(deps, {}, raw_entities=["LA", "Santa"])
    state, node = await turn(deps, state, raw_entities=["Denver"], intent="answer")

    assert node == "load_facts"
    assert state["airports"] == ["DEN"]
    assert state["clarify_queue"] == []
    assert state["clarify_answered"] == {}


async def test_small_talk_keeps_the_question_and_costs_no_attempt(deps):
    state, _ = await turn(deps, {}, raw_entities=["LA", "Santa"])
    state, node = await turn(deps, state, intent="chitchat")

    assert node == "narrate"
    assert state["clarify_attempts"] == 1
    assert [q["term"] for q in state["clarify_queue"]] == ["LA", "Santa"]

    state, _ = await turn(deps, state, raw_entities=["LAX"])
    assert state["clarify_answered"] == {"LA": ["LAX"]}


async def test_scope_question_uses_the_same_loop(deps, monkeypatch):
    import sys

    # nodes/__init__ rebinds the name to the function, so reach the module.
    module = sys.modules["app.agent.nodes.resolve_entities"]
    monkeypatch.setattr(module, "SCOPE_ASK_ABOVE", 2)

    state, node = await turn(deps, {}, intent="rank", region="California")
    assert node == "narrate"
    assert state["clarification"]["kind"] == "scope"

    state, node = await turn(deps, state, intent="rank", region="California",
                             raw_entities=["mumble"])
    assert state["clarification"]["attempt"] == 2

    state, node = await turn(deps, state, intent="rank", region="California",
                             scope_count=3)
    assert node == "load_metrics"
    assert state["result_limit"] == 3
    assert SCOPE_KEY not in state["clarify_answered"]


async def test_graph_wires_the_loop_back_to_resolution(monkeypatch):
    from langgraph.checkpoint.memory import MemorySaver

    import app.agent.graph as graph_module
    from app.agent.graph import build_graph

    # Diagram export renders via mermaid.ink; tests must not touch the network.
    monkeypatch.setattr(graph_module, "_export_diagram", lambda compiled: None)

    compiled = build_graph(MemorySaver(), SimpleNamespace())
    edges = {(e.source, e.target) for e in compiled.get_graph().edges}

    assert ("resolve_entities", "clarify") in edges
    assert ("clarify", "resolve_entities") in edges
    assert ("clarify", "narrate") in edges

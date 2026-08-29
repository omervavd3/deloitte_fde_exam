import logging
from functools import partial
from pathlib import Path

from langgraph.graph import END, START, StateGraph

from app.agent import nodes
from app.agent.deps import Deps
from app.agent.state import AgentState

log = logging.getLogger(__name__)

GRAPH_IMAGE = Path(__file__).with_name("graph.png")


def _export_diagram(compiled) -> None:
    """Render the compiled graph next to this module. Fail-soft.

    draw_mermaid_png() renders via mermaid.ink, so this needs network; a
    missing diagram must never take down startup.
    """
    try:
        GRAPH_IMAGE.write_bytes(compiled.get_graph().draw_mermaid_png())
        log.info("graph diagram written: %s", GRAPH_IMAGE)
    except Exception as exc:
        log.warning("could not render graph diagram: %s", exc)


def _after_resolve(state: AgentState) -> str:
    if state.get("clarification"):
        return "narrate"
    if state.get("intent") in ("out_of_scope", "chitchat"):
        return "narrate"
    if state.get("intent") == "answer":
        # A direct question wants a fact, not a ranking: look the airports up
        # and answer, skipping scoring and the live enrichment it feeds.
        return "load_facts"
    return "load_metrics"


def build_graph(checkpointer, deps: Deps):
    g = StateGraph(AgentState)

    g.add_node("parse_intent", partial(nodes.parse_intent, deps))
    g.add_node("resolve_entities", partial(nodes.resolve_entities, deps))
    g.add_node("load_facts", partial(nodes.load_facts, deps))
    g.add_node("load_metrics", partial(nodes.load_metrics, deps))
    g.add_node("score", partial(nodes.score, deps))
    g.add_node("enrich_live", partial(nodes.enrich_live, deps))
    g.add_node("narrate", partial(nodes.narrate, deps))

    g.add_edge(START, "parse_intent")
    g.add_edge("parse_intent", "resolve_entities")
    g.add_conditional_edges("resolve_entities", _after_resolve,
                            {"load_metrics": "load_metrics",
                             "load_facts": "load_facts",
                             "narrate": "narrate"})
    g.add_edge("load_facts", "narrate")
    g.add_edge("load_metrics", "score")
    g.add_edge("score", "enrich_live")
    g.add_edge("enrich_live", "narrate")
    g.add_edge("narrate", END)

    compiled = g.compile(checkpointer=checkpointer)
    _export_diagram(compiled)
    return compiled

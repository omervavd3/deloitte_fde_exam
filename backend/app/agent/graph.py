from langgraph.graph import END, START, StateGraph

from app.agent import nodes
from app.agent.state import AgentState


def _after_resolve(state: AgentState) -> str:
    if state.get("clarification"):
        return "narrate"
    if state.get("intent") == "out_of_scope":
        return "narrate"
    return "load_metrics"


def build_graph(checkpointer):
    g = StateGraph(AgentState)

    g.add_node("parse_intent", nodes.parse_intent)
    g.add_node("resolve_entities", nodes.resolve_entities)
    g.add_node("load_metrics", nodes.load_metrics)
    g.add_node("score", nodes.score)
    g.add_node("enrich_live", nodes.enrich_live)
    g.add_node("narrate", nodes.narrate)

    g.add_edge(START, "parse_intent")
    g.add_edge("parse_intent", "resolve_entities")
    g.add_conditional_edges("resolve_entities", _after_resolve,
                            {"load_metrics": "load_metrics", "narrate": "narrate"})
    g.add_edge("load_metrics", "score")
    g.add_edge("score", "enrich_live")
    g.add_edge("enrich_live", "narrate")
    g.add_edge("narrate", END)

    return g.compile(checkpointer=checkpointer)

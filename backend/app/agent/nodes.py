"""Graph nodes.

parse_intent and narrate call the LLM. Everything else is deterministic:
no node except those two may produce a number the user sees.
"""

from app.agent.state import AgentState


async def parse_intent(state: AgentState) -> dict:
    """LLM: question -> intent, entity strings, profile name. No numbers."""
    raise NotImplementedError


async def resolve_entities(state: AgentState) -> dict:
    """Deterministic: entity strings -> IATA codes / region. Sets clarification
    when a name like 'LA' maps to several airports."""
    raise NotImplementedError


async def load_metrics(state: AgentState) -> dict:
    """Deterministic: pull the relevant rows from the provider."""
    raise NotImplementedError


async def score(state: AgentState) -> dict:
    """Deterministic: normalize, weight, rank. Pure call into app.scoring."""
    raise NotImplementedError


async def enrich_live(state: AgentState) -> dict:
    """Live FAA/OpenSky lookups. Advisory only, never feeds the score. Fail-soft."""
    raise NotImplementedError


async def narrate(state: AgentState) -> dict:
    """LLM: explain the computed results. May only restate numbers in state."""
    raise NotImplementedError

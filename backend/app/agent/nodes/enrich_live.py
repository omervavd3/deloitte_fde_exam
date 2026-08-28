from app.agent.state import AgentState


async def enrich_live(state: AgentState) -> dict:
    """Live FAA/OpenSky lookups. Advisory only, never feeds the score. Fail-soft."""
    raise NotImplementedError

from app.agent.state import AgentState


async def resolve_entities(state: AgentState) -> dict:
    """Deterministic: entity strings -> IATA codes / region.

    Sets clarification when a name like 'LA' maps to several airports.
    """
    raise NotImplementedError

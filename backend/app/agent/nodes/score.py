from app.agent.state import AgentState


async def score(state: AgentState) -> dict:
    """Deterministic: normalize, weight, rank. Pure call into app.scoring."""
    raise NotImplementedError

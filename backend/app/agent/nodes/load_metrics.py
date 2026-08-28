from app.agent.state import AgentState


async def load_metrics(state: AgentState) -> dict:
    """Deterministic: pull the relevant rows from the provider."""
    raise NotImplementedError

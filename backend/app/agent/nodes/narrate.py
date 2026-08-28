from app.agent.state import AgentState


async def narrate(state: AgentState) -> dict:
    """LLM: explain the computed results. May only restate numbers in state."""
    raise NotImplementedError

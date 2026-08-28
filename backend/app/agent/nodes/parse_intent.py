from app.agent.state import AgentState


async def parse_intent(state: AgentState) -> dict:
    """LLM: question -> intent, entity strings, profile name. No numbers."""
    raise NotImplementedError

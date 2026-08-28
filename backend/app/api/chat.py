from fastapi import APIRouter, Request
from langchain_core.messages import HumanMessage

from app.db import repository
from app.schemas.chat import ChatRequest, ChatResponse, WeightsUsed

router = APIRouter()


@router.post("/chat")
async def chat(request: Request, payload: ChatRequest) -> ChatResponse:
    graph = request.app.state.graph
    pool = request.app.state.pool

    config = {
        "configurable": {"thread_id": str(payload.conversation_id)},
        "metadata": {"conversation_id": str(payload.conversation_id)},
        "tags": ["airport-agent"],
    }

    state = await graph.ainvoke(
        {
            "messages": [HumanMessage(payload.message)],
            "weight_overrides": payload.weight_overrides,
        },
        config,
    )
    await repository.touch_conversation(pool, payload.conversation_id)

    weights = state.get("weights")
    weights_used = (
        WeightsUsed(
            profile=state.get("profile_name", ""),
            weights=weights,
            overridden=bool(payload.weight_overrides),
        )
        if weights
        else None
    )

    return ChatResponse(
        conversation_id=payload.conversation_id,
        message=state["messages"][-1].content,
        intent=state.get("intent", "explain"),
        scores=state.get("scores", []),
        breakdown=state.get("breakdown", {}),
        weights_used=weights_used,
        live_conditions=state.get("live_conditions", []),
        assumptions=state.get("assumptions", []),
        warnings=state.get("warnings", []),
        provenance=request.app.state.provider.provenance(),
    )

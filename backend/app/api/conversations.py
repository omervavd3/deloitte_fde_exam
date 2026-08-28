from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.db import repository

router = APIRouter()


class ConversationSummary(BaseModel):
    id: UUID
    title: str


@router.get("/conversations")
async def list_conversations(request: Request) -> list[dict]:
    return await repository.list_conversations(request.app.state.pool)


@router.post("/conversations")
async def create_conversation(request: Request) -> ConversationSummary:
    conv_id = uuid4()
    title = "New conversation"
    await repository.create_conversation(request.app.state.pool, conv_id, title)
    return ConversationSummary(id=conv_id, title=title)


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(request: Request, conversation_id: UUID) -> list[dict]:
    """Replays persisted graph state so the UI can rehydrate a thread."""
    config = {"configurable": {"thread_id": str(conversation_id)}}
    snapshot = await request.app.state.graph.aget_state(config)
    messages = snapshot.values.get("messages", []) if snapshot else []
    return [{"role": m.type, "content": m.content} for m in messages]

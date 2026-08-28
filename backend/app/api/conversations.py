from uuid import UUID, uuid4

from fastapi import APIRouter, Request

from app.db import repository
from app.schemas.chat import ConversationMessage, ConversationSummary

router = APIRouter()

# LangChain message types -> the roles the API exposes.
ROLE_BY_TYPE = {"human": "user", "ai": "assistant"}


@router.get("/conversations")
async def list_conversations(request: Request) -> list[ConversationSummary]:
    rows = await repository.list_conversations(request.app.state.pool)
    return [ConversationSummary(**r) for r in rows]


@router.post("/conversations", status_code=201)
async def create_conversation(request: Request) -> ConversationSummary:
    conv_id = uuid4()
    title = "New conversation"
    await repository.create_conversation(request.app.state.pool, conv_id, title)
    return ConversationSummary(id=conv_id, title=title)


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    request: Request, conversation_id: UUID
) -> list[ConversationMessage]:
    """Replays persisted graph state so the UI can rehydrate a thread."""
    config = {"configurable": {"thread_id": str(conversation_id)}}
    snapshot = await request.app.state.graph.aget_state(config)
    messages = snapshot.values.get("messages", []) if snapshot else []

    return [
        ConversationMessage(role=ROLE_BY_TYPE[m.type], content=m.content)
        for m in messages
        if m.type in ROLE_BY_TYPE
    ]

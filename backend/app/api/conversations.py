from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request

from app.db import repository
from app.schemas.chat import (
    ChatResponse,
    ConversationMessage,
    ConversationSummary,
    ConversationUpdate,
)

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


@router.patch("/conversations/{conversation_id}")
async def rename_conversation(
    request: Request, conversation_id: UUID, payload: ConversationUpdate
) -> ConversationSummary:
    row = await repository.rename_conversation(
        request.app.state.pool, conversation_id, payload.title.strip()
    )
    if not row:
        raise HTTPException(404, f"no such conversation: {conversation_id}")
    return ConversationSummary(**row)


@router.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(request: Request, conversation_id: UUID) -> None:
    deleted = await repository.delete_conversation(
        request.app.state.pool, conversation_id
    )
    if not deleted:
        raise HTTPException(404, f"no such conversation: {conversation_id}")
    # Drop the thread's checkpoints too, so a recycled id cannot rehydrate the
    # old messages.
    await request.app.state.checkpointer.adelete_thread(str(conversation_id))


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    request: Request, conversation_id: UUID
) -> list[ConversationMessage]:
    """Replays persisted graph state so the UI can rehydrate a thread."""
    config = {"configurable": {"thread_id": str(conversation_id)}}
    snapshot = await request.app.state.graph.aget_state(config)
    messages = snapshot.values.get("messages", []) if snapshot else []
    provenance = request.app.state.provider.provenance()

    def replay(message) -> ConversationMessage:
        # Each answer carries its own numbers; graph state only holds the last
        # turn's.
        turn = message.additional_kwargs.get("turn")
        return ConversationMessage(
            role=ROLE_BY_TYPE[message.type],
            content=message.content,
            turn=ChatResponse(
                conversation_id=conversation_id,
                message=message.content,
                provenance=provenance,
                **turn,
            )
            if turn
            else None,
        )

    return [replay(m) for m in messages if m.type in ROLE_BY_TYPE]

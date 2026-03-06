import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.database import AsyncSessionLocal
from app.models.conversation import Conversation, Message
from app.services.project_service import ProjectService
from app.services.session_naming import format_session_name
from app.schemas.lora import LoraTriggerRequest, LoraTriggerResponse, LoraCallbackRequest

router = APIRouter()


async def _run_geppetto(session_id: str, project_id: str, brief: str) -> None:
    async with AsyncSessionLocal() as db:
        from app.services.gemini_agent import GeminiAgentService
        agent = GeminiAgentService(db, session_id=session_id)
        result = await agent.process_chat(brief, project_id, [])
        now = datetime.now(timezone.utc)
        db.add(Message(conversation_id=session_id, role="user", content=brief, created_at=now))
        db.add(Message(conversation_id=session_id, role="assistant", content=result.get("content", ""), created_at=now))
        convo = await db.get(Conversation, session_id)
        if convo:
            convo.updated_at = now
        await db.commit()


@router.post("/trigger", response_model=LoraTriggerResponse)
async def trigger_geppetto(
    request: LoraTriggerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    project_service = ProjectService(db)
    await project_service.ensure_project(request.project_id)

    conversation = None
    if request.session_id:
        conversation = await db.get(Conversation, request.session_id)
        if conversation and conversation.project_id != request.project_id:
            conversation = None

    if not conversation:
        now = datetime.now(timezone.utc)
        name = format_session_name(now)
        conversation = Conversation(
            project_id=request.project_id,
            name=name,
            created_at=now,
            updated_at=now,
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

    asyncio.create_task(_run_geppetto(conversation.id, request.project_id, request.brief))

    return LoraTriggerResponse(session_id=conversation.id, session_name=conversation.name)


@router.post("/callback")
async def lora_callback(
    request: LoraCallbackRequest,
    current_user: str = Depends(get_current_user)
):
    return {"received": True, "status": request.status, "session_id": request.session_id, "job_id": request.job_id}

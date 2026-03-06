from datetime import datetime, timezone
import re

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.api.deps import get_db, get_current_user
from app.schemas.agent import ChatRequest, ChatResponse
from app.models.conversation import Conversation, Message
from app.services.session_naming import format_session_name
from app.services.project_service import ProjectService
from sqlalchemy import select

router = APIRouter()

# Simple connection manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # wait for messages (rarely receive client msg apart from ping)
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest, 
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    from app.services.gemini_agent import GeminiAgentService

    project_id = request.project_id
    project_service = ProjectService(db)
    await project_service.ensure_project(project_id)

    session_id = request.session_id
    conversation = None
    if session_id:
        conversation = await db.get(Conversation, session_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Session not found")
        if conversation.project_id != request.project_id:
            raise HTTPException(status_code=400, detail="Session does not belong to project")
    else:
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
        session_id = conversation.id

    if isinstance(request.message, str):
        rename_match = re.search(r"\brename\s+(?:this\s+)?session\s+to\s+(.+)$", request.message.strip(), re.IGNORECASE)
        if rename_match:
            new_name = rename_match.group(1).strip().strip('"')
            if new_name:
                conversation.name = new_name
                conversation.updated_at = datetime.now(timezone.utc)
                db.add(Message(conversation_id=session_id, role="user", content=request.message, created_at=conversation.updated_at))
                db.add(Message(conversation_id=session_id, role="assistant", content=f"Renamed this session to {new_name}.", created_at=conversation.updated_at))
                await db.commit()
                return ChatResponse(
                    content=f"Renamed this session to {new_name}.",
                    tool_calls_executed=0,
                    cost_usd=0.0,
                    session_id=session_id,
                    session_name=conversation.name,
                )

    history: list[dict] = []
    if session_id:
        history_rows = await db.execute(
            select(Message)
            .where(Message.conversation_id == session_id)
            .order_by(Message.created_at.asc())
        )
        history = [{"role": m.role, "content": m.content} for m in history_rows.scalars().all()]
    elif request.conversation_history:
        history = [{"role": m.role, "content": m.content} for m in request.conversation_history]

    agent = GeminiAgentService(db, session_id=session_id)
    result = await agent.process_chat(request.message, request.project_id or "default_project", history)

    now = datetime.now(timezone.utc)
    db.add(Message(conversation_id=session_id, role="user", content=request.message, created_at=now))
    db.add(Message(conversation_id=session_id, role="assistant", content=result.get("content", ""), created_at=now))
    conversation.updated_at = now
    await db.commit()

    return ChatResponse(
        content=result.get("content", "Error processing request."),
        tool_calls_executed=result.get("tool_calls_executed", 0),
        cost_usd=result.get("cost_usd", 0.0),
        session_id=session_id,
        session_name=conversation.name if conversation else None,
    )

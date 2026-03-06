from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.api.deps import get_db, get_current_user
from app.schemas.agent import ChatRequest, ChatResponse

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
    agent = GeminiAgentService(db)
    
    # Pass the full conversation history sent by the client
    history = [{"role": m.role, "content": m.content} for m in (request.conversation_history or [])]
    result = await agent.process_chat(request.message, request.project_id or "default_project", history)
    
    return ChatResponse(
        content=result.get("content", "Error processing request."),
        tool_calls_executed=result.get("tool_calls_executed", 0),
        cost_usd=result.get("cost_usd", 0.0)
    )

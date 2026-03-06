from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    project_id: str
    model: Optional[str] = "claude-sonnet-4-5"
    conversation_history: Optional[List[ChatMessage]] = None
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    content: str
    tool_calls_executed: int
    cost_usd: float
    session_id: Optional[str] = None
    session_name: Optional[str] = None

from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    project_id: str
    model: Optional[str] = "claude-sonnet-4-5"
    conversation_history: Optional[List[ChatMessage]] = []

class ChatResponse(BaseModel):
    content: str
    tool_calls_executed: int
    cost_usd: float

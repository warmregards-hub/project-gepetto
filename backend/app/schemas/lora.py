from pydantic import BaseModel
from typing import Optional


class LoraTriggerRequest(BaseModel):
    brief: str
    project_id: str
    session_id: Optional[str] = None


class LoraTriggerResponse(BaseModel):
    session_id: str
    session_name: Optional[str] = None


class LoraCallbackRequest(BaseModel):
    job_id: Optional[str] = None
    session_id: Optional[str] = None
    status: Optional[str] = None

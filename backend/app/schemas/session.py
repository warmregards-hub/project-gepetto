from pydantic import BaseModel
from typing import List, Optional


class SessionCreate(BaseModel):
    project_id: str
    name: Optional[str] = None


class SessionMessage(BaseModel):
    id: str
    role: str
    content: str
    created_at: str


class SessionAsset(BaseModel):
    id: str
    asset_type: str
    drive_url: Optional[str] = None
    drive_direct_url: Optional[str] = None
    created_at: str


class SessionSummary(BaseModel):
    id: str
    name: str
    project_id: str
    created_at: str
    updated_at: Optional[str] = None
    message_count: int
    asset_count: int
    last_activity: str


class SessionDetail(BaseModel):
    id: str
    name: str
    project_id: str
    created_at: str
    updated_at: Optional[str] = None
    messages: List[SessionMessage]
    assets: List[SessionAsset]

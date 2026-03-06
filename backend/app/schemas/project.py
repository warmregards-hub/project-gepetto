from pydantic import BaseModel
from typing import Optional, Dict, Any

class ProjectCreate(BaseModel):
    name: str
    client_id: str

class ProjectResponse(BaseModel):
    id: str
    name: str
    client_id: str
    folder_path: str

class PreferenceUpdate(BaseModel):
    project_id: str
    updates: Dict[str, Any]

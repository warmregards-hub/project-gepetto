from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user

router = APIRouter()

@router.get("/")
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    # Return fake list for Phase 1 testing
    return [
        {"id": "drew-5trips", "name": "Drew (5TRIPS / BaySmokes)", "folder_path": "projects/drew-5trips"},
        {"id": "betway-f1", "name": "Betway F1", "folder_path": "projects/betway-f1"}
    ]

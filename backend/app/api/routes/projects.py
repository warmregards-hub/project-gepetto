from fastapi import APIRouter, Depends
from typing import List
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.project import Project

router = APIRouter()

@router.get("/")
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    try:
        result = await db.execute(select(Project))
        projects = result.scalars().all()
        if projects:
            return [
                {
                    "id": p.name,
                    "name": p.name,
                    "folder_path": p.folder_path,
                }
                for p in projects
            ]
    except Exception:
        pass

    projects_dir = Path("projects")
    if projects_dir.exists():
        items = []
        for entry in projects_dir.iterdir():
            if not entry.is_dir():
                continue
            if entry.name == "global":
                continue
            items.append({"id": entry.name, "name": entry.name, "folder_path": str(entry)})
        if items:
            return items

    return []

from fastapi import APIRouter, Depends
from typing import List
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.project import Project, Client

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
            try:
                for item in items:
                    project_name = item["id"]
                    result = await db.execute(select(Project).where(Project.name == project_name))
                    existing = result.scalar_one_or_none()
                    if existing:
                        continue

                    client_name = project_name.split("-")[0].replace("_", " ").strip().title() or "Unknown"
                    result = await db.execute(select(Client).where(Client.name == client_name))
                    client = result.scalar_one_or_none()
                    if not client:
                        client = Client(name=client_name)
                        db.add(client)
                        await db.flush()

                    db.add(Project(id=project_name, name=project_name, folder_path=f"projects/{project_name}", client_id=client.id))

                await db.commit()
            except Exception:
                pass
            return items

    return []

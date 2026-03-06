from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, Client, CostEntry
from app.models.conversation import Conversation
from app.models.generation import GenerationJob


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ensure_project(self, project_slug: str) -> Project:
        project = await self.db.get(Project, project_slug)
        if project:
            return project

        result = await self.db.execute(select(Project).where(Project.name == project_slug))
        project = result.scalar_one_or_none()
        if project:
            if project.id != project_slug:
                old_id = project.id
                await self.db.execute(update(Project).where(Project.id == old_id).values(id=project_slug))
                await self.db.execute(update(Conversation).where(Conversation.project_id == old_id).values(project_id=project_slug))
                await self.db.execute(update(GenerationJob).where(GenerationJob.project_id == old_id).values(project_id=project_slug))
                await self.db.execute(update(CostEntry).where(CostEntry.project_id == old_id).values(project_id=project_slug))
                await self.db.commit()
                project.id = project_slug
            return project

        client_name = project_slug.split("-")[0].replace("_", " ").strip().title() or "Unknown"
        result = await self.db.execute(select(Client).where(Client.name == client_name))
        client = result.scalar_one_or_none()
        if not client:
            client = Client(name=client_name)
            self.db.add(client)
            await self.db.flush()

        project = Project(
            id=project_slug,
            name=project_slug,
            folder_path=f"projects/{project_slug}",
            client_id=client.id,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

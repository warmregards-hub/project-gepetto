from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.project import CostEntry
from app.config import settings

class CostTracker:
    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def log_cost(
        self,
        amount_usd: float,
        service: str,
        model: str,
        project_id: str,
        description: str,
        session_id: str | None = None,
    ):
        # MOCK_GENERATION logic: If mock is enabled, visual generation shouldn't cost anything.
        final_cost = amount_usd
        if settings.mock_generation and service in ["kie-image", "kie-video", "kie-vision"]:
            final_cost = 0.0
            
        print(f"[Project Gepetto Cost] {service} ({model}) for {project_id}: ${final_cost:.4f} - {description}")

        entry = CostEntry(
            project_id=project_id,
            session_id=session_id,
            service=service,
            model=model,
            amount_usd=final_cost,
            description=description,
        )
        try:
            self.db.add(entry)
            await self.db.commit()
        except ProgrammingError as e:
            await self.db.rollback()
            print(f"[Project Gepetto Cost] Skipping cost log (table missing?): {e}")
            return final_cost

        daily_total, monthly_total, _, session_total = await self.get_totals(project_id, session_id)
        limit_target = session_total if session_id else daily_total
        if limit_target > settings.cost_limit_session or monthly_total > settings.cost_limit_monthly:
            print("[Project Gepetto Cost] Limit exceeded, consider stopping execution.")

        return final_cost

    async def get_totals(self, project_id: str | None = None, session_id: str | None = None):
        now = datetime.now(timezone.utc)
        session_start = now - timedelta(hours=24)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        daily_query = select(func.coalesce(func.sum(CostEntry.amount_usd), 0.0)).where(
            CostEntry.created_at >= session_start
        )
        month_query = select(func.coalesce(func.sum(CostEntry.amount_usd), 0.0)).where(
            CostEntry.created_at >= month_start
        )
        session_query = None
        if session_id:
            session_query = select(func.coalesce(func.sum(CostEntry.amount_usd), 0.0)).where(
                CostEntry.session_id == session_id
            )

        try:
            project_total = 0.0
            if project_id:
                project_query = select(func.coalesce(func.sum(CostEntry.amount_usd), 0.0)).where(
                    CostEntry.project_id == project_id
                )
                project_total = (await self.db.execute(project_query)).scalar_one()

            daily_total = (await self.db.execute(daily_query)).scalar_one()
            monthly_total = (await self.db.execute(month_query)).scalar_one()
            session_total = 0.0
            if session_query is not None:
                session_total = (await self.db.execute(session_query)).scalar_one()

            return daily_total, monthly_total, project_total, session_total
        except ProgrammingError as e:
            await self.db.rollback()
            print(f"[Project Gepetto Cost] Skipping totals query (table missing?): {e}")
            return 0.0, 0.0, 0.0, 0.0

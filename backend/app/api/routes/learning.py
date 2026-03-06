from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user

router = APIRouter()

from app.services.learning_engine import LearningEngine
from app.services.cost_tracker import CostTracker
from app.config import settings
from pydantic import BaseModel
from typing import Optional

class QCDecisionRequest(BaseModel):
    project_id: str
    asset_url: str
    decision: str # "keep" or "reject"
    prompt: Optional[str] = ""


class MockModeRequest(BaseModel):
    enabled: bool

@router.get("/preferences/{project_id}")
async def get_preferences(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    le = LearningEngine()
    return await le.get_preferences(project_id)

@router.post("/log-qc")
async def log_qc_decision(
    request: QCDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    le = LearningEngine()
    prompt = request.prompt or ""
    model = None
    if not prompt:
        record = await le.find_generation_by_asset(request.project_id, request.asset_url)
        if record:
            prompt = record.get("prompt") or ""
            model = record.get("model")
    await le.log_qc_decision(request.project_id, request.asset_url, request.decision, prompt, model)
    regeneration = None
    if request.decision == "reject":
        try:
            from app.services.gemini_agent import GeminiAgentService
            agent = GeminiAgentService(db)
            regen_result = await agent.regenerate_rejected_asset(request.project_id, request.asset_url)
            if regen_result.get("ok"):
                regeneration = {
                    "message": regen_result.get("message"),
                    "download_links": regen_result.get("download_links", []),
                    "pending_tasks": regen_result.get("pending_tasks", []),
                }
        except Exception:
            regeneration = None
    return {"status": "success", "regeneration": regeneration}


@router.get("/costs/totals")
async def get_cost_totals(
    project_id: Optional[str] = None,
    session_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    tracker = CostTracker(db)
    daily_total, monthly_total, project_total, session_total = await tracker.get_totals(project_id, session_id)
    return {
        "daily_total": daily_total,
        "session_total": session_total,
        "monthly_total": monthly_total,
        "project_total": project_total,
    }


@router.get("/mock")
async def get_mock_mode(current_user: str = Depends(get_current_user)):
    return {"mock_generation": settings.mock_generation}


@router.put("/mock")
async def set_mock_mode(
    request: MockModeRequest,
    current_user: str = Depends(get_current_user)
):
    settings.mock_generation = request.enabled
    return {"mock_generation": settings.mock_generation}

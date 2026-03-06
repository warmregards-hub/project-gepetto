from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.schemas.generation import ImageGenerationRequest, VideoGenerationRequest

router = APIRouter()

@router.post("/images")
async def create_image_generation_job(
    request: ImageGenerationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    # Phase 4 Studio functionality
    return {"status": "ok", "job_id": "stub_job_id"}

@router.post("/videos")
async def create_video_generation_job(
    request: VideoGenerationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    # Phase 4 Studio functionality
    return {"status": "ok", "job_id": "stub_job_id"}

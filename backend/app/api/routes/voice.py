from fastapi import APIRouter, Depends, HTTPException
import httpx
from pydantic import BaseModel
from pathlib import Path

from app.api.deps import get_current_user
from app.config import settings
from app.services.kie_client import KieClient
from app.services.cost_tracker import CostTracker
from app.api.deps import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/signed-url")
async def get_signed_url(
    agent_id: str,
    current_user: str = Depends(get_current_user)
):
    if not settings.elevenlabs_api_key:
        raise HTTPException(status_code=400, detail="ElevenLabs API key missing")

    url = "https://api.elevenlabs.io/v1/convai/conversation/get_signed_url"
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
    }
    params = {
        "agent_id": agent_id,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url, headers=headers, params=params)
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=response.text or "Failed to get signed url")
        data = response.json()
        signed_url = data.get("signed_url")
        if not signed_url:
            raise HTTPException(status_code=500, detail="Signed url missing")
        return {"signed_url": signed_url}


@router.get("/kie-trace/latest")
async def get_latest_kie_trace(
    current_user: str = Depends(get_current_user)
):
    trace_path = Path(settings.kie_trace_path)
    if not trace_path.exists():
        return {"entry": None}
    try:
        with open(trace_path, "r", encoding="utf-8") as f:
            lines = f.read().strip().splitlines()
        if not lines:
            return {"entry": None}
        return {"entry": lines[-1]}
    except Exception:
        return {"entry": None}

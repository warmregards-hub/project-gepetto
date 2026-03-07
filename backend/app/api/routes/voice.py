from fastapi import APIRouter, Depends, HTTPException
import httpx
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.config import settings
from app.services.kie_client import KieClient
from app.services.cost_tracker import CostTracker
from app.api.deps import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


class BriefFormatRequest(BaseModel):
    transcript: str
    project_id: str
    session_id: str | None = None


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


@router.post("/format-brief")
async def format_brief(
    request: BriefFormatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    if not request.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript is empty")

    system_prompt = (
        "You are a creative brief formatter. Convert a raw conversation transcript into a clean, actionable brief. "
        "Only include details about the creative request. Exclude small talk, meta commentary, or references to the agent. "
        "Return plain text only. Do not include a preamble. "
        "Include only sections that have concrete information. "
        "Use these section titles when applicable: Summary, Deliverables, Specs, Style/Creative Direction, Models/Tools, "
        "Constraints/Do-Not. "
        "If critical information is missing, omit it instead of calling it out. "
        "Keep it concise."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": request.transcript.strip()},
    ]

    client = KieClient()
    response = await client.chat_completion(messages)
    content = ""
    try:
        content = response["choices"][0]["message"]["content"]
    except Exception:
        content = ""

    if not content:
        raise HTTPException(status_code=500, detail="Failed to format brief")

    tracker = CostTracker(db)
    await tracker.log_cost(
        0.0,
        "kie-chat",
        "gemini-2.5-flash",
        request.project_id,
        "Voice brief formatting",
        session_id=request.session_id,
    )

    return {"brief": content}

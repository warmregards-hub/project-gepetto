from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.conversation import Conversation, Message
from app.models.generation import GeneratedAsset
from app.schemas.session import SessionSummary, SessionDetail, SessionCreate, SessionMessage, SessionAsset
from app.services.session_naming import format_session_name

router = APIRouter()


def _format_iso(dt: datetime | None) -> str:
    if not dt:
        return datetime.now(timezone.utc).isoformat()
    return dt.isoformat()


@router.get("/", response_model=list[SessionSummary])
async def list_sessions(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.project_id == project_id)
        .order_by(Conversation.updated_at.desc().nullslast(), Conversation.created_at.desc())
    )
    conversations = result.scalars().all()
    if not conversations:
        return []

    ids = [c.id for c in conversations]
    message_counts = {}
    asset_counts = {}

    msg_rows = await db.execute(
        select(Message.conversation_id, func.count(Message.id))
        .where(Message.conversation_id.in_(ids))
        .group_by(Message.conversation_id)
    )
    for cid, count in msg_rows.all():
        message_counts[cid] = int(count)

    asset_rows = await db.execute(
        select(GeneratedAsset.conversation_id, func.count(GeneratedAsset.id))
        .where(GeneratedAsset.conversation_id.in_(ids))
        .group_by(GeneratedAsset.conversation_id)
    )
    for cid, count in asset_rows.all():
        asset_counts[cid] = int(count)

    items: list[SessionSummary] = []
    for convo in conversations:
        updated_at = convo.updated_at or convo.created_at
        items.append(
            SessionSummary(
                id=convo.id,
                name=convo.name or "Session",
                project_id=convo.project_id,
                created_at=_format_iso(convo.created_at),
                updated_at=_format_iso(convo.updated_at) if convo.updated_at else None,
                message_count=message_counts.get(convo.id, 0),
                asset_count=asset_counts.get(convo.id, 0),
                last_activity=_format_iso(updated_at),
            )
        )
    return items


@router.post("/", response_model=SessionSummary)
async def create_session(
    request: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    now = datetime.now(timezone.utc)
    name = request.name or format_session_name(now)
    convo = Conversation(
        project_id=request.project_id,
        name=name,
        created_at=now,
        updated_at=now,
    )
    db.add(convo)
    await db.commit()
    await db.refresh(convo)
    return SessionSummary(
        id=convo.id,
        name=convo.name or "Session",
        project_id=convo.project_id,
        created_at=_format_iso(convo.created_at),
        updated_at=_format_iso(convo.updated_at) if convo.updated_at else None,
        message_count=0,
        asset_count=0,
        last_activity=_format_iso(convo.updated_at or convo.created_at),
    )


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    convo = await db.get(Conversation, session_id)
    if not convo:
        raise HTTPException(status_code=404, detail="Session not found")

    msg_rows = await db.execute(
        select(Message).where(Message.conversation_id == session_id).order_by(Message.created_at.asc())
    )
    asset_rows = await db.execute(
        select(GeneratedAsset).where(GeneratedAsset.conversation_id == session_id).order_by(GeneratedAsset.created_at.asc())
    )

    messages = [
        SessionMessage(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            created_at=_format_iso(msg.created_at),
        )
        for msg in msg_rows.scalars().all()
    ]

    assets = [
        SessionAsset(
            id=asset.id,
            asset_type=asset.asset_type,
            drive_url=asset.drive_url,
            drive_direct_url=asset.drive_direct_url,
            created_at=_format_iso(asset.created_at),
        )
        for asset in asset_rows.scalars().all()
    ]

    return SessionDetail(
        id=convo.id,
        name=convo.name or "Session",
        project_id=convo.project_id,
        created_at=_format_iso(convo.created_at),
        updated_at=_format_iso(convo.updated_at) if convo.updated_at else None,
        messages=messages,
        assets=assets,
    )

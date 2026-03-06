from datetime import datetime, timezone

from fastapi import APIRouter, Request, BackgroundTasks
import httpx
import json
from pathlib import Path
from app.services.storage_service import StorageService
from app.services.learning_engine import LearningEngine
from app.services.drive_service import DriveService
from app.services.notification_service import NotificationService
from app.database import AsyncSessionLocal
from app.models.generation import GeneratedAsset
from app.models.conversation import Conversation
import time

router = APIRouter()

async def process_kie_callback(data: dict, project_id: str | None = None, session_id: str | None = None):
    # This background task downloads the completed files from Kie.ai to storage
    task_id = data.get("task_id") or data.get("id")
    status = data.get("status", "").lower()
    
    if status not in ("succeeded", "completed", "success"):
        print(f"[Project Gepetto] Kie callback failed or pending for task {task_id}: {status}")
        return

    result = data.get("output") or data.get("data") or data.get("result") or []
    urls = []
    if isinstance(result, list):
        urls = [r.get("url") or r for r in result if r]
    elif isinstance(result, dict) and result.get("url"):
        urls = [result.get("url")]

    if not urls:
        print(f"[Project Gepetto] No URLs found in Kie callback for task {task_id}")
        return

    # Download and save
    storage = StorageService()
    project_id = project_id or data.get("client_id") or data.get("project_id") or "default"
    ts = int(time.time())
    drive = DriveService()
    notifier = NotificationService()
    
    saved_links = []
    async with httpx.AsyncClient() as client:
        for i, url in enumerate(urls):
            if isinstance(url, str) and url.startswith("http"):
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    ext = "jpg"
                    if ".mp4" in url.lower(): ext = "mp4"
                    elif ".png" in url.lower(): ext = "png"
                    filename = f"webhook_gen_{ts}_{i}.{ext}"
                    saved_path = await storage.save_file(resp.content, project_id, "webhook", filename)
                    asset_type = "video" if ext == "mp4" else "image"
                    drive_info = None
                    if drive.is_enabled():
                        drive_info = drive.upload_bytes(filename, resp.content)
                        if drive_info:
                            try:
                                Path(saved_path).unlink(missing_ok=True)
                            except Exception:
                                pass
                    direct_link = drive_info.get("directUrl") if drive_info else None
                    saved_links.append(direct_link or f"/api/storage/download/{project_id}/webhook/{filename}")
                    if session_id:
                        async with AsyncSessionLocal() as db:
                            asset = GeneratedAsset(
                                job_id=None,
                                conversation_id=session_id,
                                asset_type=asset_type,
                                file_path=saved_path,
                                drive_id=drive_info.get("id") if drive_info else None,
                                drive_url=drive_info.get("webViewLink") if drive_info else None,
                                drive_direct_url=drive_info.get("directUrl") if drive_info else None,
                                original_prompt="",
                            )
                            db.add(asset)
                            convo = await db.get(Conversation, session_id)
                            if convo:
                                convo.updated_at = datetime.now(timezone.utc)
                            await db.commit()
                except Exception as e:
                    print(f"Failed to download {url}: {e}")

    print(f"[Project Gepetto] Webhook saved files for task {task_id}: {saved_links}")
    try:
        le = LearningEngine()
        param = data.get("param")
        prompt = ""
        model = data.get("model") or ""
        aspect_ratio = ""
        if isinstance(param, str):
            try:
                parsed = json.loads(param)
                model = parsed.get("model") or model
                input_data = parsed.get("input") if isinstance(parsed.get("input"), dict) else {}
                prompt = input_data.get("prompt") or prompt
                aspect_ratio = input_data.get("aspect_ratio") or ""
            except Exception:
                pass
        size_map = {"9:16": "1024x1792", "16:9": "1792x1024", "1:1": "1024x1024", "4:3": "1024x768", "3:4": "768x1024"}
        size = size_map.get(aspect_ratio, "1024x1024")
        batch_id = str(task_id or ts)
        for idx, link in enumerate(saved_links):
            await le.log_generation(project_id, link, prompt, model, size, batch_id, idx)
    except Exception:
        pass

    try:
        if saved_links:
            await notifier.notify("Geppetto Complete", f"Generated {len(saved_links)} asset(s).", saved_links[0])
    except Exception:
        pass

    try:
        from app.api.routes.agent import manager
        if saved_links:
            body = "\n".join([f"![variant_{idx}]({link})" for idx, link in enumerate(saved_links)])
            content = f"Generated {len(saved_links)}.\n\n{body}"
            await manager.broadcast({"type": "asset_update", "data": {"message": content}})
    except Exception:
        pass

@router.post("/callback")
async def kie_webhook_callback(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    session_id = request.query_params.get("session_id")
    project_id = request.query_params.get("project_id")
    print(f"[Project Gepetto] Received Kie webhook: {data.get('task_id')}")
    # We must respond 200 immediately to the webhook provider
    background_tasks.add_task(process_kie_callback, data, project_id, session_id)
    return {"received": True}

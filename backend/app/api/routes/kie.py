from fastapi import APIRouter, Request, BackgroundTasks
import httpx
from pathlib import Path
from app.services.storage_service import StorageService
import time

router = APIRouter()

async def process_kie_callback(data: dict):
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
    project_id = data.get("client_id") or data.get("project_id") or "default"
    ts = int(time.time())
    
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
                    await storage.save_file(resp.content, project_id, "webhook", filename)
                    saved_links.append(f"/api/storage/download/{project_id}/webhook/{filename}")
                except Exception as e:
                    print(f"Failed to download {url}: {e}")

    print(f"[Project Gepetto] Webhook saved files for task {task_id}: {saved_links}")
    # Push update to frontend via WebSocket (Implementation pending WebSocket integration details)
    # from app.api.routes.agent import agent_connections (or similar)

@router.post("/callback")
async def kie_webhook_callback(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    print(f"[Project Gepetto] Received Kie webhook: {data.get('task_id')}")
    # We must respond 200 immediately to the webhook provider
    background_tasks.add_task(process_kie_callback, data)
    return {"received": True}
